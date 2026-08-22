//! The input-script format shared by `just probe`, `just probe-file` and
//! `just film`.
//!
//! Deliberately hand-rolled rather than `serde_json`: `crates/sim` earns its
//! guarantees from having almost no dependency graph at all
//! (`tests/boundary.rs` reads the real one), and a fifty-line reader for a
//! format this small is a better trade than a new edge in that graph.
//!
//! A script file is:
//!
//! ```json
//! {"version": 1, "inputs": [{"nudge_up": true}, {}, {"nudge_down": true}]}
//! ```
//!
//! Every element is an object of [`Intents`] fields; omitted fields are false,
//! and reading past the end of `inputs` yields all-false. When the game's input
//! type changes, change [`intents_from_object`] with it — that function is the
//! whole coupling between the wire format and the simulation.

use crate::Intents;

/// Fields accepted inside one input object. Update alongside [`Intents`].
const INPUT_FIELDS: &[&str] = &["nudge_up", "nudge_down"];

/// Parse one JSON object of input fields, e.g. `{"nudge_up": true}`.
///
/// An empty or whitespace-only string means "all inputs false", which is what
/// makes a blank line on the probe's stdin a legal idle tick.
pub fn parse_intents(text: &str) -> Result<Intents, String> {
    if text.trim().is_empty() {
        return Ok(Intents::default());
    }
    let value = Json::parse(text)?;
    intents_from_object(&value)
}

/// Parse a whole script file into one [`Intents`] per tick.
pub fn parse_script(text: &str) -> Result<Vec<Intents>, String> {
    let value = Json::parse(text)?;
    let Json::Object(fields) = &value else {
        return Err(format!(
            "a script must be a JSON object like {{\"version\": 1, \"inputs\": [...]}}, found {}",
            value.kind()
        ));
    };

    for (key, _) in fields {
        if key != "version" && key != "inputs" {
            return Err(format!(
                "unknown script field {key:?}; expected \"version\" and \"inputs\""
            ));
        }
    }

    match fields.iter().find(|(key, _)| key == "version") {
        Some((_, Json::Number(n))) if *n == 1.0 => {}
        Some((_, other)) => {
            return Err(format!(
                "unsupported script version {}; this build understands version 1",
                other.render()
            ));
        }
        None => return Err("script is missing \"version\": 1".to_owned()),
    }

    let Some((_, Json::Array(items))) = fields.iter().find(|(key, _)| key == "inputs") else {
        return Err("script is missing an \"inputs\" array".to_owned());
    };

    items
        .iter()
        .enumerate()
        .map(|(index, item)| {
            intents_from_object(item).map_err(|why| format!("inputs[{index}]: {why}"))
        })
        .collect()
}

/// The one place the wire format meets the simulation's input type.
fn intents_from_object(value: &Json) -> Result<Intents, String> {
    let Json::Object(fields) = value else {
        return Err(format!(
            "expected an object of input fields, found {}",
            value.kind()
        ));
    };
    let mut intents = Intents::default();
    for (key, field) in fields {
        let Json::Bool(on) = field else {
            return Err(format!(
                "field {key:?} must be true or false, found {}",
                field.kind()
            ));
        };
        match key.as_str() {
            "nudge_up" => intents.nudge_up = *on,
            "nudge_down" => intents.nudge_down = *on,
            other => {
                return Err(format!(
                    "unknown input field {other:?}; this game accepts {INPUT_FIELDS:?}"
                ));
            }
        }
    }
    Ok(intents)
}

// --------------------------------------------------------------------------
// A very small JSON reader
// --------------------------------------------------------------------------

#[derive(Debug, Clone, PartialEq)]
enum Json {
    Null,
    Bool(bool),
    Number(f64),
    Str(String),
    Array(Vec<Json>),
    Object(Vec<(String, Json)>),
}

impl Json {
    fn kind(&self) -> &'static str {
        match self {
            Json::Null => "null",
            Json::Bool(_) => "a boolean",
            Json::Number(_) => "a number",
            Json::Str(_) => "a string",
            Json::Array(_) => "an array",
            Json::Object(_) => "an object",
        }
    }

    fn render(&self) -> String {
        match self {
            Json::Null => "null".to_owned(),
            Json::Bool(v) => v.to_string(),
            Json::Number(v) => v.to_string(),
            Json::Str(v) => format!("{v:?}"),
            Json::Array(_) => "an array".to_owned(),
            Json::Object(_) => "an object".to_owned(),
        }
    }

    fn parse(text: &str) -> Result<Json, String> {
        let mut reader = Reader {
            bytes: text.as_bytes(),
            at: 0,
        };
        let value = reader.value()?;
        reader.skip_space();
        if reader.at < reader.bytes.len() {
            return Err(format!("trailing text at byte {}", reader.at));
        }
        Ok(value)
    }
}

struct Reader<'a> {
    bytes: &'a [u8],
    at: usize,
}

impl Reader<'_> {
    fn skip_space(&mut self) {
        while matches!(self.bytes.get(self.at), Some(b' ' | b'\t' | b'\n' | b'\r')) {
            self.at += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.bytes.get(self.at).copied()
    }

    fn expect(&mut self, byte: u8) -> Result<(), String> {
        if self.peek() == Some(byte) {
            self.at += 1;
            Ok(())
        } else {
            Err(format!("expected {:?} at byte {}", byte as char, self.at))
        }
    }

    fn literal(&mut self, word: &str) -> Result<(), String> {
        if self.bytes[self.at..].starts_with(word.as_bytes()) {
            self.at += word.len();
            Ok(())
        } else {
            Err(format!("expected {word:?} at byte {}", self.at))
        }
    }

    fn value(&mut self) -> Result<Json, String> {
        self.skip_space();
        match self.peek() {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => self.string().map(Json::Str),
            Some(b't') => self.literal("true").map(|()| Json::Bool(true)),
            Some(b'f') => self.literal("false").map(|()| Json::Bool(false)),
            Some(b'n') => self.literal("null").map(|()| Json::Null),
            Some(_) => self.number(),
            None => Err("unexpected end of input".to_owned()),
        }
    }

    fn object(&mut self) -> Result<Json, String> {
        self.expect(b'{')?;
        let mut fields = Vec::new();
        self.skip_space();
        if self.peek() == Some(b'}') {
            self.at += 1;
            return Ok(Json::Object(fields));
        }
        loop {
            self.skip_space();
            let key = self.string()?;
            self.skip_space();
            self.expect(b':')?;
            fields.push((key, self.value()?));
            self.skip_space();
            match self.peek() {
                Some(b',') => self.at += 1,
                Some(b'}') => {
                    self.at += 1;
                    return Ok(Json::Object(fields));
                }
                _ => return Err(format!("expected ',' or '}}' at byte {}", self.at)),
            }
        }
    }

    fn array(&mut self) -> Result<Json, String> {
        self.expect(b'[')?;
        let mut items = Vec::new();
        self.skip_space();
        if self.peek() == Some(b']') {
            self.at += 1;
            return Ok(Json::Array(items));
        }
        loop {
            items.push(self.value()?);
            self.skip_space();
            match self.peek() {
                Some(b',') => self.at += 1,
                Some(b']') => {
                    self.at += 1;
                    return Ok(Json::Array(items));
                }
                _ => return Err(format!("expected ',' or ']' at byte {}", self.at)),
            }
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.expect(b'"')?;
        let mut out = String::new();
        loop {
            let Some(byte) = self.peek() else {
                return Err("unterminated string".to_owned());
            };
            self.at += 1;
            match byte {
                b'"' => return Ok(out),
                b'\\' => {
                    let Some(escape) = self.peek() else {
                        return Err("unterminated escape".to_owned());
                    };
                    self.at += 1;
                    match escape {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => out.push(self.unicode_escape()?),
                        other => {
                            return Err(format!("unknown escape \\{}", other as char));
                        }
                    }
                }
                // Multi-byte UTF-8 arrives here one byte at a time; collecting
                // the raw bytes and validating at the end would be faster, but
                // this format is a handful of ASCII field names.
                _ => {
                    let start = self.at - 1;
                    let end = (start + 4).min(self.bytes.len());
                    let text = core::str::from_utf8(&self.bytes[start..end])
                        .map(|s| s.chars().next())
                        .unwrap_or(None);
                    let Some(ch) = text else {
                        return Err(format!("invalid UTF-8 at byte {start}"));
                    };
                    out.push(ch);
                    self.at = start + ch.len_utf8();
                }
            }
        }
    }

    fn unicode_escape(&mut self) -> Result<char, String> {
        let end = self.at + 4;
        if end > self.bytes.len() {
            return Err("truncated \\u escape".to_owned());
        }
        let hex = core::str::from_utf8(&self.bytes[self.at..end])
            .map_err(|_| "invalid \\u escape".to_owned())?;
        let code = u32::from_str_radix(hex, 16).map_err(|_| "invalid \\u escape".to_owned())?;
        self.at = end;
        char::from_u32(code).ok_or_else(|| format!("\\u{hex} is not a character"))
    }

    fn number(&mut self) -> Result<Json, String> {
        let start = self.at;
        while matches!(
            self.peek(),
            Some(b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9')
        ) {
            self.at += 1;
        }
        let text = core::str::from_utf8(&self.bytes[start..self.at])
            .map_err(|_| "invalid number".to_owned())?;
        text.parse::<f64>()
            .map(Json::Number)
            .map_err(|_| format!("{text:?} is not a number (at byte {start})"))
    }
}
