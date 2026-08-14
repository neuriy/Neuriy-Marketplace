using System.ComponentModel.DataAnnotations;
using Microsoft.AspNetCore.Http;

namespace NeuriyMarketplace.Web.Models;

public class UploadAppViewModel
{
    [Required, StringLength(120)]
    public string Name { get; set; } = string.Empty;

    [Required, StringLength(4000)]
    public string Description { get; set; } = string.Empty;

    [Required, StringLength(80)]
    public string Category { get; set; } = "Utilities";

    [StringLength(120)]
    public string Developer { get; set; } = "Community";

    [StringLength(40)]
    public string Price { get; set; } = "Free";

    [StringLength(40)]
    public string Version { get; set; } = "1.0.0";

    [Required]
    public IFormFile? Package { get; set; }

    public IFormFile? Icon { get; set; }
}
