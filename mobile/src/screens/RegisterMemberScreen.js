import React, { useEffect, useState } from "react";
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
} from "react-native";
import { createMember, getPlans } from "../api";
import { useNavigation } from "@react-navigation/native";

export default function RegisterMemberScreen() {
  const nav = useNavigation();
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [amountPaid, setAmountPaid] = useState("");

  useEffect(() => {
    getPlans().then(({ data }) => {
      if (data.plans) {
        setPlans(data.plans);
        setSelectedPlan(data.plans[0]);
        setAmountPaid(String(data.plans[0]?.price ?? ""));
      }
    });
  }, []);

  const handleSubmit = async () => {
    if (!name || !phone || !selectedPlan) {
      Alert.alert("Missing info", "Please fill in name, phone, and select a plan.");
      return;
    }
    setLoading(true);
    try {
      const { data } = await createMember({
        name, phone, address,
        plan_id: selectedPlan.id,
        amount_paid: amountPaid || selectedPlan.price,
        extra_json: "{}",
        csrf_token: "",
      });
      if (data.success) {
        Alert.alert("✅ Registered!", `${name} has been registered.`, [
          { text: "OK", onPress: () => nav.goBack() }
        ]);
      } else {
        Alert.alert("Error", data.error || "Could not register member.");
      }
    } catch {
      Alert.alert("Error", "Network error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
      <ScrollView style={s.root}>
        <Text style={s.title}>Register New Member</Text>

        <Label>Full Name *</Label>
        <TextInput style={s.input} value={name} onChangeText={setName} placeholder="e.g. Ravi Kumar" placeholderTextColor="#888" />

        <Label>Phone Number *</Label>
        <TextInput style={s.input} value={phone} onChangeText={setPhone} placeholder="10-digit mobile" placeholderTextColor="#888" keyboardType="phone-pad" />

        <Label>Address</Label>
        <TextInput style={[s.input, { height: 80, textAlignVertical: "top" }]} value={address} onChangeText={setAddress} placeholder="Optional" placeholderTextColor="#888" multiline />

        <Label>Select Plan *</Label>
        <View style={s.planGrid}>
          {plans.map(p => (
            <TouchableOpacity
              key={p.id}
              style={[s.planCard, selectedPlan?.id === p.id && s.planCardSelected]}
              onPress={() => { setSelectedPlan(p); setAmountPaid(String(p.price)); }}
            >
              <Text style={s.planName}>{p.name}</Text>
              <Text style={s.planPrice}>₹{p.price}</Text>
              <Text style={s.planDays}>{p.duration_days} days</Text>
            </TouchableOpacity>
          ))}
        </View>

        <Label>Amount Paid (₹)</Label>
        <TextInput style={s.input} value={amountPaid} onChangeText={setAmountPaid} keyboardType="numeric" placeholderTextColor="#888" />

        <TouchableOpacity style={s.btn} onPress={handleSubmit} disabled={loading}>
          {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Register Member</Text>}
        </TouchableOpacity>
        <View style={{ height: 40 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Label({ children }) {
  return <Text style={{ color: "#aaa", fontSize: 12, marginBottom: 6, marginTop: 14 }}>{children}</Text>;
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e", padding: 20 },
  title: { fontSize: 22, fontWeight: "800", color: "#fff", marginBottom: 8 },
  input: { backgroundColor: "#16213e", color: "#fff", borderRadius: 10, padding: 14, fontSize: 15 },
  planGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 4 },
  planCard: { flex: 1, minWidth: 100, backgroundColor: "#16213e", borderRadius: 12, padding: 14, borderWidth: 2, borderColor: "transparent", alignItems: "center" },
  planCardSelected: { borderColor: "#e94560" },
  planName: { color: "#fff", fontWeight: "700", fontSize: 13 },
  planPrice: { color: "#e94560", fontWeight: "800", fontSize: 18, marginTop: 4 },
  planDays: { color: "#aaa", fontSize: 11, marginTop: 2 },
  btn: { backgroundColor: "#e94560", borderRadius: 12, padding: 16, alignItems: "center", marginTop: 24 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
