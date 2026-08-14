using Microsoft.AspNetCore.Mvc;
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
    public IActionResult Register() => View(new Models.RegisterViewModel());

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Register(Models.RegisterViewModel model, CancellationToken cancellationToken)
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
    public IActionResult Login(string? returnUrl = null)
    {
        ViewBag.ReturnUrl = returnUrl;
        return View(new Models.LoginViewModel());
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public async Task<IActionResult> Login(Models.LoginViewModel model, string? returnUrl, CancellationToken cancellationToken)
    {
        if (!ModelState.IsValid)
        {
            ViewBag.ReturnUrl = returnUrl;
            return View(model);
        }

        try
        {
            var auth = await _api.LoginAsync(model, cancellationToken);
            SaveSession(auth);
            if (!string.IsNullOrWhiteSpace(returnUrl) && Url.IsLocalUrl(returnUrl))
            {
                return Redirect(returnUrl);
            }

            return RedirectToAction("Index", "Home");
        }
        catch (Exception ex)
        {
            ModelState.AddModelError(string.Empty, ex.Message);
            ViewBag.ReturnUrl = returnUrl;
            return View(model);
        }
    }

    [HttpGet]
    public async Task<IActionResult> Profile(CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(HttpContext.Session.GetString("AccessToken")))
        {
            return RedirectToAction(nameof(Login), new { returnUrl = Url.Action(nameof(Profile)) });
        }

        var me = await _api.MeAsync(cancellationToken);
        if (me is null)
        {
            HttpContext.Session.Clear();
            return RedirectToAction(nameof(Login));
        }

        return View(me);
    }

    [HttpGet]
    public IActionResult Settings()
    {
        if (string.IsNullOrWhiteSpace(HttpContext.Session.GetString("AccessToken")))
        {
            return RedirectToAction(nameof(Login), new { returnUrl = Url.Action(nameof(Settings)) });
        }

        ViewBag.Username = HttpContext.Session.GetString("Username");
        ViewBag.Role = HttpContext.Session.GetString("Role");
        return View();
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    public IActionResult Logout()
    {
        HttpContext.Session.Clear();
        return RedirectToAction("Index", "Home");
    }

    private void SaveSession(Models.AuthResponse auth)
    {
        HttpContext.Session.SetString("AccessToken", auth.AccessToken);
        HttpContext.Session.SetString("Username", auth.User.Username);
        HttpContext.Session.SetString("Role", auth.User.Role);
        HttpContext.Session.SetString("UserId", auth.User.Id);
        HttpContext.Session.SetString("Email", auth.User.Email);
    }
}
