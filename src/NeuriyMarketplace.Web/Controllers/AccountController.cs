using Microsoft.AspNetCore.Mvc;
using NeuriyMarketplace.Web.Models;
using NeuriyMarketplace.Web.Services;

namespace NeuriyMarketplace.Web.Controllers;

public class AccountController : Controller
{
    private readonly MarketplaceApiClient _api;

    public AccountController(MarketplaceApiClient api)
    {
        _api = api;
    }

    [HttpGet]
    public IActionResult Register() => View(new RegisterViewModel());

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Register(RegisterViewModel model, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return View(model);
        }

        try
        {
            var auth = await _api.RegisterAsync(model, cancellationToken);
            SaveSession(auth);
            TempData["Success"] = auth.User.Role == "admin"
                ? "Welcome. You are the first account, so you are the marketplace admin."
                : "Account created.";
            return RedirectToAction("Index", "Home");
        }
        catch (Exception ex)
        {
            ModelState.AddModelError(string.Empty, ex.Message);
            return View(model);
        }
    }

    [HttpGet]
    public IActionResult Login() => View(new LoginViewModel());

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Login(LoginViewModel model, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            return View(model);
        }

        try
        {
            var auth = await _api.LoginAsync(model, cancellationToken);
            SaveSession(auth);
            return RedirectToAction("Index", "Home");
        }
        catch (Exception ex)
        {
            ModelState.AddModelError(string.Empty, ex.Message);
            return View(model);
        }
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public IActionResult Logout()
    {
        HttpContext.Session.Clear();
        return RedirectToAction("Index", "Home");
    }

    private void SaveSession(AuthResponse auth)
    {
        HttpContext.Session.SetString("AccessToken", auth.AccessToken);
        HttpContext.Session.SetString("Username", auth.User.Username);
        HttpContext.Session.SetString("Role", auth.User.Role);
        HttpContext.Session.SetString("UserId", auth.User.Id);
    }
}
