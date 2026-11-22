import React, { useEffect, useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert, TextInput,
} from "react-native";
import { getPlans, renewMembership } from "../api";
import { useNavigation, useRoute } from "@react-navigation/native";

export default function RenewMembershipScreen() {
  const nav = useNavigation();
  const route = useRoute();
  const { memberId, memberName } = route.params;

  const [plans, setPlans] = useState([]);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [amountPaid, setAmountPaid] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getPlans().then(({ data }) => {
      if (data.plans) {
        setPlans(data.plans);
        setSelectedPlan(data.plans[0]);
        setAmountPaid(String(data.plans[0]?.price ?? ""));
      }
    });
  }, []);

  const handleRenew = async () => {
    if (!selectedPlan) return;
    setLoading(true);
    try {
      const { data } = await renewMembership(memberId, selectedPlan.id, amountPaid || selectedPlan.price);
      if (data.success) {
        Alert.alert("✅ Renewed!", `Membership valid until ${data.end_date}`, [
          { text: "OK", onPress: () => nav.goBack() }
        ]);
      } else {
        Alert.alert("Error", data.error || "Could not renew.");
      }
    } catch {
      Alert.alert("Error", "Network error.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView style={s.root}>
      <Text style={s.title}>Renew — {memberName}</Text>

      <Text style={s.label}>Select Plan</Text>
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

      <Text style={s.label}>Amount Paid (₹)</Text>
      <TextInput
        style={s.input}
        value={amountPaid}
        onChangeText={setAmountPaid}
        keyboardType="numeric"
        placeholderTextColor="#888"
      />

      <TouchableOpacity style={s.btn} onPress={handleRenew} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>🔄 Confirm Renewal</Text>}
      </TouchableOpacity>
    </ScrollView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e", padding: 20 },
  title: { fontSize: 20, fontWeight: "800", color: "#fff", marginBottom: 20 },
  label: { color: "#aaa", fontSize: 12, marginBottom: 8, marginTop: 16 },
  input: { backgroundColor: "#16213e", color: "#fff", borderRadius: 10, padding: 14, fontSize: 15 },
  planGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  planCard: { flex: 1, minWidth: 100, backgroundColor: "#16213e", borderRadius: 12, padding: 14, borderWidth: 2, borderColor: "transparent", alignItems: "center" },
  planCardSelected: { borderColor: "#e94560" },
  planName: { color: "#fff", fontWeight: "700", fontSize: 13 },
  planPrice: { color: "#e94560", fontWeight: "800", fontSize: 18, marginTop: 4 },
  planDays: { color: "#aaa", fontSize: 11, marginTop: 2 },
  btn: { backgroundColor: "#e94560", borderRadius: 12, padding: 16, alignItems: "center", marginTop: 28 },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
