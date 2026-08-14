using System.ComponentModel.DataAnnotations;

namespace NeuriyMarketplace.Web.Models;

public class RegisterViewModel
{
    [Required, EmailAddress, StringLength(200)]
    public string Email { get; set; } = string.Empty;

    [Required, StringLength(40, MinimumLength = 3)]
    public string Username { get; set; } = string.Empty;

    [Required, StringLength(128, MinimumLength = 8), DataType(DataType.Password)]
    public string Password { get; set; } = string.Empty;
}

public class LoginViewModel
{
    [Required, StringLength(200)]
    public string Login { get; set; } = string.Empty;

    [Required, StringLength(128, MinimumLength = 8), DataType(DataType.Password)]
    public string Password { get; set; } = string.Empty;
}

public class MarketplaceUser
{
    public string Id { get; set; } = string.Empty;
    public string Email { get; set; } = string.Empty;
    public string Username { get; set; } = string.Empty;
    public string Role { get; set; } = "user";
    public DateTime CreatedAt { get; set; }
}

public class AuthResponse
{
    public string AccessToken { get; set; } = string.Empty;
    public string TokenType { get; set; } = "bearer";
    public MarketplaceUser User { get; set; } = new();
}

public class MarketplaceRule
{
    public string Id { get; set; } = string.Empty;
    public string Code { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Severity { get; set; } = "block";
    public string? Pattern { get; set; }
    public int? MinDescriptionLength { get; set; }
    public int Enabled { get; set; } = 1;
    public int IsSystem { get; set; }
    public string? CreatedBy { get; set; }
    public DateTime CreatedAt { get; set; }
}

public class RuleCreateViewModel
{
    [Required, StringLength(120)]
    public string Title { get; set; } = string.Empty;

    [Required, StringLength(1000)]
    public string Description { get; set; } = string.Empty;

    [Required]
    public string Severity { get; set; } = "block";

    [StringLength(300)]
    public string? Pattern { get; set; }

    public int? MinDescriptionLength { get; set; }

    [StringLength(60)]
    public string? Code { get; set; }
}

public class AdminDashboardViewModel
{
    public IReadOnlyList<MarketplaceUser> Users { get; set; } = Array.Empty<MarketplaceUser>();
    public IReadOnlyList<MarketplaceRule> Rules { get; set; } = Array.Empty<MarketplaceRule>();
    public IReadOnlyList<MarketplaceApp> Queue { get; set; } = Array.Empty<MarketplaceApp>();
    public RuleCreateViewModel NewRule { get; set; } = new();
}
