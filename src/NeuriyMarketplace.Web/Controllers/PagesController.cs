using Microsoft.AspNetCore.Mvc;

namespace NeuriyMarketplace.Web.Controllers;

public class PagesController : Controller
{
    [HttpGet]
    public IActionResult About() => View();

    [HttpGet]
    public IActionResult Developers() => View();

    [HttpGet]
    public IActionResult Support() => View();

    [HttpGet]
    public IActionResult Terms() => View();

    [HttpGet]
    public IActionResult Cookies() => View();

    [HttpGet]
    public IActionResult Community() => View();

    [HttpGet]
    public IActionResult Publishers() => View();

    [HttpGet]
    public IActionResult Sdk() => View();
}
