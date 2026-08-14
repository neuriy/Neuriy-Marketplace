namespace NeuriyMarketplace.Web.Models;

public class HomeViewModel
{
    public string? Query { get; set; }
    public string Category { get; set; } = "All Categories";
    public string Sort { get; set; } = "popular";
    public IReadOnlyList<string> Categories { get; set; } = Array.Empty<string>();
    public IReadOnlyList<MarketplaceApp> FeaturedApps { get; set; } = Array.Empty<MarketplaceApp>();
    public IReadOnlyList<MarketplaceApp> CatalogApps { get; set; } = Array.Empty<MarketplaceApp>();
}
