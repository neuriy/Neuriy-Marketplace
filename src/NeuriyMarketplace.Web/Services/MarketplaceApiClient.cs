using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using NeuriyMarketplace.Web.Models;

namespace NeuriyMarketplace.Web.Services;

public class MarketplaceApiClient
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    private readonly HttpClient _http;

    public MarketplaceApiClient(HttpClient http)
    {
        _http = http;
    }

    public async Task<IReadOnlyList<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync("/api/categories", cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        using var document = await JsonDocument.ParseAsync(stream, cancellationToken: cancellationToken);
        if (!document.RootElement.TryGetProperty("categories", out var categoriesElement))
        {
            return Array.Empty<string>();
        }

        return categoriesElement.EnumerateArray()
            .Select(item => item.GetString() ?? string.Empty)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .ToList();
    }

    public async Task<IReadOnlyList<MarketplaceApp>> GetAppsAsync(
        string? query = null,
        string? category = null,
        bool? featured = null,
        string sort = "popular",
        CancellationToken cancellationToken = default)
    {
        var queryParts = new List<string> { $"sort={Uri.EscapeDataString(sort)}" };
        if (!string.IsNullOrWhiteSpace(query))
        {
            queryParts.Add($"q={Uri.EscapeDataString(query)}");
        }

        if (!string.IsNullOrWhiteSpace(category) &&
            !category.Equals("All Categories", StringComparison.OrdinalIgnoreCase) &&
            !category.Equals("All", StringComparison.OrdinalIgnoreCase))
        {
            queryParts.Add($"category={Uri.EscapeDataString(category)}");
        }

        if (featured.HasValue)
        {
            queryParts.Add($"featured={featured.Value.ToString().ToLowerInvariant()}");
        }

        var path = "/api/apps?" + string.Join("&", queryParts);
        using var response = await _http.GetAsync(path, cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        var apps = await JsonSerializer.DeserializeAsync<List<MarketplaceApp>>(stream, JsonOptions, cancellationToken);
        return apps ?? new List<MarketplaceApp>();
    }

    public async Task<MarketplaceApp?> GetAppAsync(string id, CancellationToken cancellationToken = default)
    {
        using var response = await _http.GetAsync($"/api/apps/{Uri.EscapeDataString(id)}", cancellationToken);
        if (response.StatusCode == System.Net.HttpStatusCode.NotFound)
        {
            return null;
        }

        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonSerializer.DeserializeAsync<MarketplaceApp>(stream, JsonOptions, cancellationToken);
    }

    public async Task<MarketplaceApp> UploadAppAsync(UploadAppViewModel model, CancellationToken cancellationToken = default)
    {
        if (model.Package is null || model.Package.Length == 0)
        {
            throw new InvalidOperationException("Package file is required.");
        }

        using var form = new MultipartFormDataContent();
        form.Add(new StringContent(model.Name), "name");
        form.Add(new StringContent(model.Description), "description");
        form.Add(new StringContent(model.Category), "category");
        form.Add(new StringContent(model.Developer), "developer");
        form.Add(new StringContent(model.Price), "price");
        form.Add(new StringContent(model.Version), "version");
        form.Add(new StringContent("false"), "featured");

        await using var packageBuffer = new MemoryStream();
        await model.Package.CopyToAsync(packageBuffer, cancellationToken);
        var packageBytes = packageBuffer.ToArray();
        var packageContent = new ByteArrayContent(packageBytes);
        packageContent.Headers.ContentType = new MediaTypeHeaderValue(model.Package.ContentType ?? "application/octet-stream");
        form.Add(packageContent, "package", model.Package.FileName);

        if (model.Icon is { Length: > 0 })
        {
            await using var iconBuffer = new MemoryStream();
            await model.Icon.CopyToAsync(iconBuffer, cancellationToken);
            var iconContent = new ByteArrayContent(iconBuffer.ToArray());
            iconContent.Headers.ContentType = new MediaTypeHeaderValue(model.Icon.ContentType ?? "application/octet-stream");
            form.Add(iconContent, "icon", model.Icon.FileName);
        }

        using var response = await _http.PostAsync("/api/apps", form, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException($"Upload failed ({(int)response.StatusCode}): {body}");
        }

        var created = JsonSerializer.Deserialize<MarketplaceApp>(body, JsonOptions);
        return created ?? throw new InvalidOperationException("API returned an empty app payload.");
    }

    public async Task<(Stream Stream, string FileName, string ContentType)> DownloadAppAsync(
        string id,
        CancellationToken cancellationToken = default)
    {
        var response = await _http.GetAsync($"/api/apps/{Uri.EscapeDataString(id)}/download", HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        response.EnsureSuccessStatusCode();
        var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        var fileName = response.Content.Headers.ContentDisposition?.FileNameStar
                       ?? response.Content.Headers.ContentDisposition?.FileName?.Trim('"')
                       ?? $"neuriy-app-{id}.neuriy";
        var contentType = response.Content.Headers.ContentType?.ToString() ?? "application/octet-stream";

        // Copy into memory so HttpResponseMessage can be disposed safely by caller lifecycle
        var memory = new MemoryStream();
        await stream.CopyToAsync(memory, cancellationToken);
        memory.Position = 0;
        response.Dispose();
        return (memory, fileName, contentType);
    }
}
