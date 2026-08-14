namespace NeuriyMarketplace.Web.Models;

public class MarketplaceApp
{
    public string Id { get; set; } = string.Empty;
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Category { get; set; } = string.Empty;
    public string Developer { get; set; } = string.Empty;
    public string Price { get; set; } = "Free";
    public string Version { get; set; } = "1.0.0";
    public double Rating { get; set; }
    public int Downloads { get; set; }
    public bool Featured { get; set; }
    public string? IconUrl { get; set; }
    public string? PackageFilename { get; set; }
    public DateTime CreatedAt { get; set; }
    public DateTime UpdatedAt { get; set; }
}
