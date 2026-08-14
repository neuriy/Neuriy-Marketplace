using Microsoft.AspNetCore.Mvc;
using NeuriyMarketplace.Web.Models;
using NeuriyMarketplace.Web.Services;

namespace NeuriyMarketplace.Web.Controllers;

public class AdminController : Controller
{
    private readonly MarketplaceApiClient _api;

    public AdminController(MarketplaceApiClient api)
    {
        _api = api;
    }

    private bool IsModerator =>
        string.Equals(HttpContext.Session.GetString("Role"), "admin", StringComparison.OrdinalIgnoreCase) ||
        string.Equals(HttpContext.Session.GetString("Role"), "administrator", StringComparison.OrdinalIgnoreCase);

    private bool IsAdmin =>
        string.Equals(HttpContext.Session.GetString("Role"), "admin", StringComparison.OrdinalIgnoreCase);

    [HttpGet]
    public async Task<IActionResult> Index(CancellationToken cancellationToken)
    {
        if (!IsModerator)
        {
            return RedirectToAction("Login", "Account");
        }

        var model = new AdminDashboardViewModel
        {
            Rules = await _api.GetRulesAsync(cancellationToken),
            Queue = await _api.GetModerationQueueAsync(cancellationToken),
            Users = IsAdmin ? await _api.GetUsersAsync(cancellationToken) : Array.Empty<MarketplaceUser>()
        };
        return View(model);
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> CreateRule(RuleCreateViewModel newRule, CancellationToken cancellationToken)
    {
        if (!IsModerator)
        {
            return RedirectToAction("Login", "Account");
        }

        if (!ModelState.IsValid)
        {
            TempData["Error"] = "Rule form is incomplete.";
            return RedirectToAction(nameof(Index));
        }

        try
        {
            await _api.CreateRuleAsync(newRule, cancellationToken);
            TempData["Success"] = "Rule added.";
        }
        catch (Exception ex)
        {
            TempData["Error"] = ex.Message;
        }

        return RedirectToAction(nameof(Index));
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> SetRole(string userId, string role, CancellationToken cancellationToken)
    {
        if (!IsAdmin)
        {
            return Forbid();
        }

        try
        {
            await _api.SetRoleAsync(userId, role, cancellationToken);
            TempData["Success"] = "Role updated.";
        }
        catch (Exception ex)
        {
            TempData["Error"] = ex.Message;
        }

        return RedirectToAction(nameof(Index));
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> SetStatus(string appId, string status, CancellationToken cancellationToken)
    {
        if (!IsModerator)
        {
            return RedirectToAction("Login", "Account");
        }

        try
        {
            await _api.SetAppStatusAsync(appId, status, cancellationToken: cancellationToken);
            TempData["Success"] = $"App marked {status}.";
        }
        catch (Exception ex)
        {
            TempData["Error"] = ex.Message;
        }

        return RedirectToAction(nameof(Index));
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Remoderate(string appId, CancellationToken cancellationToken)
    {
        if (!IsModerator)
        {
            return RedirectToAction("Login", "Account");
        }

        try
        {
            var app = await _api.RemoderateAsync(appId, cancellationToken);
            TempData["Success"] = $"Re-scored “{app.Name}” → {app.Status} ({app.ModerationScore:0}).";
        }
        catch (Exception ex)
        {
            TempData["Error"] = ex.Message;
        }

        return RedirectToAction(nameof(Index));
    }
}
