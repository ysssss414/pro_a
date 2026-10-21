//! Text-only B1 full-request conversion/encoding. No transport or inference.
use deepseek_recipe::openai::ChatCompletionRequest;
use deepseek_recipe::request::{ConversionOptions, ProtocolRequest};
use deepseek_recipe_core::messages::InputMessage;
use deepseek_recipe_encoding::{PromptEncoding, PromptTokenizer, v4::dsv41::DeepseekV41Encoding};
use serde_json::{Value, json};
use tokenizers::Tokenizer;
use std::{env, fs, path::Path};

fn encode(value: &Value, tokenizer: &Tokenizer) -> Result<(Vec<u32>, String, Value, Value, String), Box<dyn std::error::Error>> {
    // Local conversion only: the API wire retains deepseek-flash. This pins an
    // encoding family, not a claim about server weights or exact server usage.
    let mut local = value.clone();
    if local["model"] == "deepseek-flash" { local["model"] = json!("DeepSeek-V4.1-Flash"); }
    let request: ChatCompletionRequest = serde_json::from_value(local)?;
    let converted = request.convert(ConversionOptions::default())?;
    let conversation = &converted.conversation;
    let mut messages = Vec::new();
    for message in &conversation.messages {
        let (role, content) = match message {
            InputMessage::System {content, ..} => ("system", content.as_str()),
            InputMessage::User {content, ..} => ("user", content.as_str()),
            _ => return Err("B1 counter domain is System/User text only".into()),
        };
        messages.push(json!({"role": role, "content": content}));
    }
    let tools: Vec<_> = conversation.tools.iter().map(|t| json!({"name": t.name,
        "description": t.description, "parameters": t.parameters, "strict": t.strict,
        "defer_loading": t.defer_loading})).collect();
    let projection = json!({"messages": messages, "thinking_mode": conversation.thinking_mode,
        "tools": tools, "tool_choice": format!("{:?}", conversation.tool_choice),
        "reasoning_effort": format!("{:?}", conversation.reasoning_effort),
        "response_format": format!("{:?}", conversation.response_format), "stream": converted.stream,
        "max_tokens": converted.inference_options.max_tokens,
        "temperature": converted.inference_options.temperature, "top_p": converted.inference_options.top_p});
    let debug = format!("{converted:#?}");
    let encoding = DeepseekV41Encoding::new().with_tokenizer(PromptTokenizer::new(tokenizer));
    let rendered = encoding.render_conversation(conversation);
    if !rendered.image_sources.is_empty() { return Err("B1 counter is text-only".into()); }
    let structure = json!({"explicit_special_ranges": rendered.special_ranges.iter()
        .map(|r| json!([r.start, r.end])).collect::<Vec<_>>(), "image_sources": 0});
    Ok((encoding.encode(conversation)?, rendered.prompt, projection, structure, debug))
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    let value: Value = serde_json::from_slice(&fs::read(&args[1])?)?;
    let tokenizer = Tokenizer::from_file(&args[2]).map_err(|e| e.to_string())?;
    let (tokens, prompt, converted, structure, debug) = encode(&value, &tokenizer)?;
    let mut base = value.clone();
    base.as_object_mut().unwrap().remove("tools");
    base.as_object_mut().unwrap().remove("tool_choice");
    for m in base["messages"].as_array_mut().unwrap() { m["content"] = json!(""); }
    let n0 = encode(&base, &tokenizer)?.0.len();
    base["messages"][0]["content"] = value["messages"][0]["content"].clone();
    let n1 = encode(&base, &tokenizer)?.0.len();
    base["messages"][1]["content"] = value["messages"][1]["content"].clone();
    let n2 = encode(&base, &tokenizer)?.0.len();
    let out = Path::new(&args[3]); fs::create_dir_all(out)?;
    fs::write(out.join("rendered-prompt.txt"), &prompt)?;
    fs::write(out.join("token-ids.json"), serde_json::to_vec(&tokens)?)?;
    fs::write(out.join("converted.json"), serde_json::to_vec_pretty(&converted)?)?;
    fs::write(out.join("converted-debug.txt"), debug)?;
    fs::write(out.join("rendered-structure.json"), serde_json::to_vec_pretty(&structure)?)?;
    let report = json!({"encoder":"DeepseekV41Encoding", "input_tokens":tokens.len(),
        "rendered_prompt_utf8_bytes":prompt.len(), "server_usage_exact":false,
        "recipe_commit":"935817c66f5d6e64838f419692545f06787e485f",
        "sequential_ablation":{"empty_role_template":n0,"with_system":n1,"with_system_user":n2,
            "with_tools_and_forced_tool_choice":tokens.len()},
        "allocation":{"template_base":n0,"system_delta":n1 as i64-n0 as i64,
            "user_delta":n2 as i64-n1 as i64,"tool_schema_and_tool_template_delta":tokens.len() as i64-n2 as i64}});
    fs::write(out.join("local-token-count.json"), serde_json::to_vec_pretty(&report)?)?;
    println!("{}", serde_json::to_string(&report)?);
    Ok(())
}
