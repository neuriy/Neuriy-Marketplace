using Microsoft.AspNetCore.Mvc;
using NeuriyMarketplace.Web.Models;
using NeuriyMarketplace.Web.Services;

namespace NeuriyMarketplace.Web.Controllers;

public class AppsController : Controller
{
    private readonly MarketplaceApiClient _api;
    private readonly IConfiguration _configuration;
    private readonly ILogger<AppsController> _logger;

    public AppsController(MarketplaceApiClient api, IConfiguration configuration, ILogger<AppsController> logger)
    {
        _api = api;
        _configuration = configuration;
        _logger = logger;
    }

    [HttpGet]
    public async Task<IActionResult> Details(string id, CancellationToken cancellationToken)
    {
        var app = await _api.GetAppAsync(id, cancellationToken);
        if (app is null)
        {
            return NotFound();
        }

        ViewBag.ApiBaseUrl = _configuration["MarketplaceApi:BaseUrl"] ?? "http://127.0.0.1:8000";
        return View(app);
    }

    [HttpGet]
    public async Task<IActionResult> Upload(CancellationToken cancellationToken)
    {
        ViewBag.Categories = await SafeCategories(cancellationToken);
        return View(new UploadAppViewModel());
    }

    [HttpPost]
    [ValidateAntiForgeryToken]
    [RequestSizeLimit(104_857_600)]
    public async Task<IActionResult> Upload(UploadAppViewModel model, CancellationToken cancellationToken)
    {
        ViewBag.Categories = await SafeCategories(cancellationToken);

        if (!ModelState.IsValid)
        {
            return View(model);
        }

        try
        {
            var created = await _api.UploadAppAsync(model, cancellationToken);
            TempData["Success"] = $"“{created.Name}” was published to Neuriy Marketplace.";
            return RedirectToAction(nameof(Details), new { id = created.Id });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to upload app");
            ModelState.AddModelError(string.Empty, "Upload failed. Ensure the Python API is running and the package file is valid.");
            return View(model);
        }
    }

    [HttpGet]
    public async Task<IActionResult> Download(string id, CancellationToken cancellationToken)
    {
        try
        {
            var (stream, fileName, contentType) = await _api.DownloadAppAsync(id, cancellationToken);
            return File(stream, contentType, fileName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Download failed for {AppId}", id);
            return NotFound();
        }
    }

    private async Task<IReadOnlyList<string>> SafeCategories(CancellationToken cancellationToken)
    {
        try
        {
            var categories = await _api.GetCategoriesAsync(cancellationToken);
            return categories.Where(c => !c.Equals("All Categories", StringComparison.OrdinalIgnoreCase)).ToList();
        }
        catch
        {
            return new[]
            {
                "Assistants", "Productivity", "Creative", "Developer Tools",
                "Research", "Education", "Utilities"
            };
        }
    }
}
