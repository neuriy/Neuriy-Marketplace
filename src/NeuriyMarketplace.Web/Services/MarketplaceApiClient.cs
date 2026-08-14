using System.Net.Http.Headers;
using System.Text;
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
    private readonly IHttpContextAccessor _httpContextAccessor;

    public MarketplaceApiClient(HttpClient http, IHttpContextAccessor httpContextAccessor)
    {
        _http = http;
        _httpContextAccessor = httpContextAccessor;
    }

    private void ApplyAuth()
    {
        _http.DefaultRequestHeaders.Authorization = null;
        var token = _httpContextAccessor.HttpContext?.Session.GetString("AccessToken");
        if (!string.IsNullOrWhiteSpace(token))
        {
            _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", token);
        }
    }

    public async Task<AuthResponse> RegisterAsync(RegisterViewModel model, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        var payload = JsonSerializer.Serialize(new
        {
            email = model.Email,
            username = model.Username,
            password = model.Password
        });
        using var response = await _http.PostAsync(
            "/api/auth/register",
            new StringContent(payload, Encoding.UTF8, "application/json"),
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Registration failed"));
        }

        return JsonSerializer.Deserialize<AuthResponse>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty auth response");
    }

    public async Task<AuthResponse> LoginAsync(LoginViewModel model, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        var payload = JsonSerializer.Serialize(new
        {
            login = model.Login,
            password = model.Password
        });
        using var response = await _http.PostAsync(
            "/api/auth/login",
            new StringContent(payload, Encoding.UTF8, "application/json"),
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Login failed"));
        }

        return JsonSerializer.Deserialize<AuthResponse>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty auth response");
    }

    public async Task<MarketplaceUser?> MeAsync(CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.GetAsync("/api/auth/me", cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            return null;
        }

        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonSerializer.DeserializeAsync<MarketplaceUser>(stream, JsonOptions, cancellationToken);
    }

    public async Task<IReadOnlyList<string>> GetCategoriesAsync(CancellationToken cancellationToken = default)
    {
        ApplyAuth();
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
        ApplyAuth();
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
        ApplyAuth();
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
        ApplyAuth();
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
        var packageContent = new ByteArrayContent(packageBuffer.ToArray());
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
            throw new HttpRequestException(ExtractDetail(body, $"Upload failed ({(int)response.StatusCode})"));
        }

        return JsonSerializer.Deserialize<MarketplaceApp>(body, JsonOptions)
               ?? throw new InvalidOperationException("API returned an empty app payload.");
    }

    public async Task<(Stream Stream, string FileName, string ContentType)> DownloadAppAsync(
        string id,
        CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.GetAsync(
            $"/api/apps/{Uri.EscapeDataString(id)}/download",
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(cancellationToken);
            throw new HttpRequestException(ExtractDetail(body, "Download failed"));
        }

        var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        var fileName = response.Content.Headers.ContentDisposition?.FileNameStar
                       ?? response.Content.Headers.ContentDisposition?.FileName?.Trim('"')
                       ?? $"neuriy-app-{id}.neuriy";
        var contentType = response.Content.Headers.ContentType?.ToString() ?? "application/octet-stream";
        var memory = new MemoryStream();
        await stream.CopyToAsync(memory, cancellationToken);
        memory.Position = 0;
        return (memory, fileName, contentType);
    }

    public async Task<IReadOnlyList<MarketplaceUser>> GetUsersAsync(CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.GetAsync("/api/users", cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonSerializer.DeserializeAsync<List<MarketplaceUser>>(stream, JsonOptions, cancellationToken)
               ?? new List<MarketplaceUser>();
    }

    public async Task<MarketplaceUser> SetRoleAsync(string userId, string role, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        var payload = JsonSerializer.Serialize(new { role });
        using var response = await _http.PostAsync(
            $"/api/users/{Uri.EscapeDataString(userId)}/role",
            new StringContent(payload, Encoding.UTF8, "application/json"),
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Role update failed"));
        }

        return JsonSerializer.Deserialize<MarketplaceUser>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty user payload");
    }

    public async Task<IReadOnlyList<MarketplaceRule>> GetRulesAsync(CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.GetAsync("/api/rules", cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonSerializer.DeserializeAsync<List<MarketplaceRule>>(stream, JsonOptions, cancellationToken)
               ?? new List<MarketplaceRule>();
    }

    public async Task<MarketplaceRule> CreateRuleAsync(RuleCreateViewModel model, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        var payload = JsonSerializer.Serialize(new
        {
            title = model.Title,
            description = model.Description,
            severity = model.Severity,
            pattern = string.IsNullOrWhiteSpace(model.Pattern) ? null : model.Pattern,
            min_description_length = model.MinDescriptionLength,
            code = string.IsNullOrWhiteSpace(model.Code) ? null : model.Code
        }, JsonOptions);
        using var response = await _http.PostAsync(
            "/api/rules",
            new StringContent(payload, Encoding.UTF8, "application/json"),
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Rule create failed"));
        }

        return JsonSerializer.Deserialize<MarketplaceRule>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty rule payload");
    }

    public async Task<IReadOnlyList<MarketplaceApp>> GetModerationQueueAsync(CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.GetAsync("/api/apps/moderation/queue", cancellationToken);
        response.EnsureSuccessStatusCode();
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        return await JsonSerializer.DeserializeAsync<List<MarketplaceApp>>(stream, JsonOptions, cancellationToken)
               ?? new List<MarketplaceApp>();
    }

    public async Task<MarketplaceApp> SetAppStatusAsync(string appId, string status, string? notes = null, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        var payload = JsonSerializer.Serialize(new { status, notes }, JsonOptions);
        using var response = await _http.PostAsync(
            $"/api/apps/{Uri.EscapeDataString(appId)}/status",
            new StringContent(payload, Encoding.UTF8, "application/json"),
            cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Status update failed"));
        }

        return JsonSerializer.Deserialize<MarketplaceApp>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty app payload");
    }

    public async Task<MarketplaceApp> RemoderateAsync(string appId, CancellationToken cancellationToken = default)
    {
        ApplyAuth();
        using var response = await _http.PostAsync($"/api/apps/{Uri.EscapeDataString(appId)}/remoderate", null, cancellationToken);
        var body = await response.Content.ReadAsStringAsync(cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            throw new HttpRequestException(ExtractDetail(body, "Remoderation failed"));
        }

        return JsonSerializer.Deserialize<MarketplaceApp>(body, JsonOptions)
               ?? throw new InvalidOperationException("Empty app payload");
    }

    private static string ExtractDetail(string body, string fallback)
    {
        try
        {
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("detail", out var detail))
            {
                return detail.ValueKind == JsonValueKind.String ? detail.GetString() ?? fallback : detail.ToString();
            }
        }
        catch
        {
            // ignore parse errors
        }

        return string.IsNullOrWhiteSpace(body) ? fallback : body;
    }
}
