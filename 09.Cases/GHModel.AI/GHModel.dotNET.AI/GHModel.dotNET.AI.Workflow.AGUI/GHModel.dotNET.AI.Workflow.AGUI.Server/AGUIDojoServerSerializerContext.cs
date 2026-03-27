using System;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.Json.Serialization.Metadata;

namespace AGUIDojoServer;

internal sealed partial class AGUIDojoServerSerializerContext : JsonSerializerContext
{
	private static readonly JsonSerializerOptions s_generatedSerializerOptions = new(JsonSerializerDefaults.Web);

	public static AGUIDojoServerSerializerContext Default { get; } = new();

	public AGUIDojoServerSerializerContext() : base(s_generatedSerializerOptions)
	{
	}

	public AGUIDojoServerSerializerContext(JsonSerializerOptions options) : base(options ?? throw new ArgumentNullException(nameof(options)))
	{
	}

	protected override JsonSerializerOptions GeneratedSerializerOptions => s_generatedSerializerOptions;

	public override JsonTypeInfo? GetTypeInfo(Type type)
	{
		// No source-generated metadata is available yet; fall back to other resolvers in the chain.
		return null;
	}
}