// A very small JSON reader, used only by the probe entry points.
//
// `JsonUtility` cannot do this: it maps JSON onto a concrete serialisable type
// and silently drops anything it does not recognise, which is the opposite of
// what an input script needs. A hand-written reader is ~150 lines, has no
// dependencies, and fails loudly on malformed input.
//
// Values map to: Dictionary<string, object>, List<object>, string, double,
// bool, or null.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace Starter.EditorTools
{
    internal static class Json
    {
        public static object Parse(string text)
        {
            if (text == null) throw new ArgumentNullException(nameof(text));
            int index = 0;
            var value = ReadValue(text, ref index);
            SkipWhitespace(text, ref index);
            if (index != text.Length)
            {
                throw new FormatException(
                    $"trailing characters after the JSON value at offset {index}");
            }
            return value;
        }

        /// Read a boolean field, defaulting to false when absent. Anything
        /// present but not a boolean is an error, not a shrug: a script that
        /// says `"nudge_up": 1` is a script whose author expected something.
        public static bool Flag(IReadOnlyDictionary<string, object> obj, string key)
        {
            if (obj == null || !obj.TryGetValue(key, out var raw)) return false;
            if (raw is bool flag) return flag;
            throw new FormatException($"'{key}' must be true or false");
        }

        private static object ReadValue(string s, ref int i)
        {
            SkipWhitespace(s, ref i);
            if (i >= s.Length) throw new FormatException("unexpected end of JSON input");

            char c = s[i];
            switch (c)
            {
                case '{': return ReadObject(s, ref i);
                case '[': return ReadArray(s, ref i);
                case '"': return ReadString(s, ref i);
                case 't': Expect(s, ref i, "true"); return true;
                case 'f': Expect(s, ref i, "false"); return false;
                case 'n': Expect(s, ref i, "null"); return null;
                default: return ReadNumber(s, ref i);
            }
        }

        private static Dictionary<string, object> ReadObject(string s, ref int i)
        {
            var result = new Dictionary<string, object>(StringComparer.Ordinal);
            i++; // '{'
            SkipWhitespace(s, ref i);
            if (i < s.Length && s[i] == '}') { i++; return result; }

            while (true)
            {
                SkipWhitespace(s, ref i);
                string key = ReadString(s, ref i);
                SkipWhitespace(s, ref i);
                if (i >= s.Length || s[i] != ':')
                {
                    throw new FormatException($"expected ':' after key '{key}'");
                }
                i++;
                result[key] = ReadValue(s, ref i);
                SkipWhitespace(s, ref i);
                if (i >= s.Length) throw new FormatException("unterminated JSON object");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == '}') { i++; return result; }
                throw new FormatException($"expected ',' or '}}' at offset {i}");
            }
        }

        private static List<object> ReadArray(string s, ref int i)
        {
            var result = new List<object>();
            i++; // '['
            SkipWhitespace(s, ref i);
            if (i < s.Length && s[i] == ']') { i++; return result; }

            while (true)
            {
                result.Add(ReadValue(s, ref i));
                SkipWhitespace(s, ref i);
                if (i >= s.Length) throw new FormatException("unterminated JSON array");
                if (s[i] == ',') { i++; continue; }
                if (s[i] == ']') { i++; return result; }
                throw new FormatException($"expected ',' or ']' at offset {i}");
            }
        }

        private static string ReadString(string s, ref int i)
        {
            if (i >= s.Length || s[i] != '"')
            {
                throw new FormatException($"expected a string at offset {i}");
            }
            i++;
            var sb = new StringBuilder();
            while (i < s.Length)
            {
                char c = s[i++];
                if (c == '"') return sb.ToString();
                if (c != '\\') { sb.Append(c); continue; }

                if (i >= s.Length) break;
                char escape = s[i++];
                switch (escape)
                {
                    case '"': sb.Append('"'); break;
                    case '\\': sb.Append('\\'); break;
                    case '/': sb.Append('/'); break;
                    case 'b': sb.Append('\b'); break;
                    case 'f': sb.Append('\f'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    case 't': sb.Append('\t'); break;
                    case 'u':
                        if (i + 4 > s.Length) throw new FormatException("truncated \\u escape");
                        sb.Append((char)ushort.Parse(
                            s.AsSpan(i, 4), NumberStyles.HexNumber, CultureInfo.InvariantCulture));
                        i += 4;
                        break;
                    default: throw new FormatException($"unknown escape '\\{escape}'");
                }
            }
            throw new FormatException("unterminated JSON string");
        }

        private static double ReadNumber(string s, ref int i)
        {
            int start = i;
            while (i < s.Length && IsNumberChar(s[i])) i++;
            string token = s.Substring(start, i - start);
            if (double.TryParse(token, NumberStyles.Float, CultureInfo.InvariantCulture, out double d))
            {
                return d;
            }
            throw new FormatException($"'{token}' is not a JSON number");
        }

        private static bool IsNumberChar(char c) =>
            (c >= '0' && c <= '9') ||
            c == '+' || c == '-' || c == '.' || c == 'e' || c == 'E';

        private static void Expect(string s, ref int i, string literal)
        {
            if (i + literal.Length > s.Length ||
                string.CompareOrdinal(s, i, literal, 0, literal.Length) != 0)
            {
                throw new FormatException($"expected '{literal}' at offset {i}");
            }
            i += literal.Length;
        }

        private static void SkipWhitespace(string s, ref int i)
        {
            while (i < s.Length && (s[i] == ' ' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r')) i++;
        }
    }
}
