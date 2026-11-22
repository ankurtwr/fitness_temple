import React, { useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from "react-native";
import { login } from "../api";
import { useAuth } from "../context/AuthContext";

export default function LoginScreen() {
  const { signIn } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async () => {
    if (!username || !password) { setError("Fill in both fields."); return; }
    setLoading(true); setError("");
    try {
      const { status, data } = await login(username, password);
      if (status === 200 && data.token) {
        signIn(data.token, data.username);
      } else {
        setError(data.error || "Login failed");
      }
    } catch (e) {
      setError("Cannot reach server. Check your connection.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.root} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <View style={s.card}>
        <Text style={s.logo}>🏋️</Text>
        <Text style={s.title}>Fitness Temple</Text>
        <Text style={s.subtitle}>Admin Login</Text>

        {error ? <Text style={s.error}>{error}</Text> : null}

        <TextInput
          style={s.input}
          placeholder="Username"
          autoCapitalize="none"
          value={username}
          onChangeText={setUsername}
        />
        <TextInput
          style={s.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
        />

        <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading}>
          {loading
            ? <ActivityIndicator color="#fff" />
            : <Text style={s.btnText}>Login</Text>}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e", justifyContent: "center", padding: 24 },
  card: { backgroundColor: "#16213e", borderRadius: 16, padding: 28, alignItems: "center", elevation: 8 },
  logo: { fontSize: 48 },
  title: { fontSize: 24, fontWeight: "800", color: "#e94560", marginTop: 8 },
  subtitle: { fontSize: 14, color: "#aaa", marginBottom: 24 },
  error: { backgroundColor: "#e9456022", color: "#e94560", padding: 10, borderRadius: 8, marginBottom: 12, width: "100%", textAlign: "center" },
  input: { backgroundColor: "#0f3460", color: "#fff", borderRadius: 10, padding: 14, width: "100%", marginBottom: 14, fontSize: 15 },
  btn: { backgroundColor: "#e94560", borderRadius: 10, padding: 16, width: "100%", alignItems: "center", marginTop: 4 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
