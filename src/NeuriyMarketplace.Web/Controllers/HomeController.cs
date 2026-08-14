using Microsoft.AspNetCore.Mvc;
using NeuriyMarketplace.Web.Models;
using NeuriyMarketplace.Web.Services;

namespace NeuriyMarketplace.Web.Controllers;

public class HomeController : Controller
{
    private readonly MarketplaceApiClient _api;
    private readonly ILogger<HomeController> _logger;
    private readonly IConfiguration _configuration;

    public HomeController(MarketplaceApiClient api, ILogger<HomeController> logger, IConfiguration configuration)
    {
        _api = api;
        _logger = logger;
        _configuration = configuration;
    }

    [HttpGet]
    public async Task<IActionResult> Index(string? q, string? category, string? sort, CancellationToken cancellationToken)
    {
        var selectedCategory = string.IsNullOrWhiteSpace(category) ? "All Categories" : category;
        var selectedSort = string.Equals(sort, "new", StringComparison.OrdinalIgnoreCase) ? "new" : "popular";

        try
        {
            var categoriesTask = _api.GetCategoriesAsync(cancellationToken);
            var featuredTask = _api.GetAppsAsync(query: q, category: selectedCategory, featured: true, sort: "popular", cancellationToken: cancellationToken);
            var catalogTask = _api.GetAppsAsync(query: q, category: selectedCategory, featured: null, sort: selectedSort, cancellationToken: cancellationToken);
            await Task.WhenAll(categoriesTask, featuredTask, catalogTask);

            var model = new HomeViewModel
            {
                Query = q,
                Category = selectedCategory,
                Sort = selectedSort,
                Categories = await categoriesTask,
                FeaturedApps = await featuredTask,
                CatalogApps = await catalogTask
            };

            ViewBag.ApiBaseUrl = _configuration["MarketplaceApi:BaseUrl"] ?? "http://127.0.0.1:8000";
            return View(model);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to load marketplace home");
            ViewBag.ErrorMessage = "Marketplace API is unavailable. Start the Python API on port 8000.";
            ViewBag.ApiBaseUrl = _configuration["MarketplaceApi:BaseUrl"] ?? "http://127.0.0.1:8000";
            return View(new HomeViewModel
            {
                Query = q,
                Category = selectedCategory,
                Sort = selectedSort,
                Categories = new[]
                {
                    "All Categories", "Assistants", "Productivity", "Creative",
                    "Developer Tools", "Research", "Education", "Utilities"
                }
            });
        }
    }

    [HttpGet]
    public IActionResult Privacy()
    {
        return View();
    }

    [ResponseCache(Duration = 0, Location = ResponseCacheLocation.None, NoStore = true)]
    public IActionResult Error()
    {
        return View();
    }
}
