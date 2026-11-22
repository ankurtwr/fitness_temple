import React, { useEffect, useState } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet, ScrollView,
  ActivityIndicator, Alert,
} from "react-native";
import { getMember, startCardAssignment, checkAssignmentStatus } from "../api";
import { useNavigation, useRoute } from "@react-navigation/native";

export default function MemberDetailScreen() {
  const route = useRoute();
  const nav = useNavigation();
  const { member: initialMember } = route.params;
  const [member, setMember] = useState(initialMember);
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [assignStatus, setAssignStatus] = useState("");

  const refreshMember = async () => {
    const { data } = await getMember(initialMember.id);
    if (data.id) setMember(data);
  };

  useEffect(() => { refreshMember(); }, []);

  const handleAssignCard = async () => {
    setAssigning(true);
    setAssignStatus("Waiting for card tap...");
    try {
      const { data } = await startCardAssignment(member.id);
      if (!data.success) { Alert.alert("Error", data.error || "Failed"); setAssigning(false); return; }

      const assignmentId = data.assignment_id;
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        const { data: s } = await checkAssignmentStatus(assignmentId);
        if (s.status === "done") {
          clearInterval(poll);
          setAssigning(false);
          setAssignStatus(`✅ Card assigned: ${s.card_uid}`);
          refreshMember();
        } else if (s.status === "expired" || attempts > 35) {
          clearInterval(poll);
          setAssigning(false);
          setAssignStatus("⏱ Timed out — tap a card within 30s");
        } else {
          setAssignStatus(`Waiting for card tap... (${35 - attempts}s)`);
        }
      }, 1000);
    } catch (e) {
      setAssigning(false);
      setAssignStatus("Error starting assignment");
    }
  };

  const expiry = member.expiry_date || initialMember.expiry_date;
  const isExpired = member.is_expired ?? initialMember.is_expired;

  return (
    <ScrollView style={s.root}>
      <View style={s.card}>
        <View style={s.headerRow}>
          <View style={[s.bigAvatar, isExpired && { backgroundColor: "#555" }]}>
            <Text style={s.bigAvatarText}>{member.name[0]}</Text>
          </View>
          <View style={{ marginLeft: 16, flex: 1 }}>
            <Text style={s.name}>{member.name}</Text>
            <Text style={s.phone}>{member.phone}</Text>
            <Text style={[s.statusBadge, isExpired ? s.expired : s.active]}>
              {isExpired ? "Membership Expired" : "Active Member"}
            </Text>
          </View>
        </View>

        <View style={s.infoRow}>
          <InfoItem label="Plan" value={member.plan_name || initialMember.current_plan || "—"} />
          <InfoItem label="Expires" value={expiry || "—"} />
        </View>
        <View style={s.infoRow}>
          <InfoItem label="Card" value={initialMember.has_active_card ? "✅ Assigned" : "❌ No card"} />
        </View>
      </View>

      {/* Assign Card */}
      <View style={s.section}>
        <Text style={s.sectionTitle}>Card Assignment</Text>
        {assigning ? (
          <View style={{ alignItems: "center", padding: 16 }}>
            <ActivityIndicator color="#e94560" />
            <Text style={s.assignMsg}>{assignStatus}</Text>
          </View>
        ) : (
          <>
            {assignStatus ? <Text style={s.assignMsg}>{assignStatus}</Text> : null}
            <TouchableOpacity style={s.btn} onPress={handleAssignCard}>
              <Text style={s.btnText}>📡 Assign RFID Card</Text>
            </TouchableOpacity>
          </>
        )}
      </View>

      {/* Renew */}
      <View style={s.section}>
        <Text style={s.sectionTitle}>Membership</Text>
        <TouchableOpacity
          style={[s.btn, s.btnSecondary]}
          onPress={() => nav.navigate("RenewMembership", { memberId: member.id, memberName: member.name })}
        >
          <Text style={s.btnText}>🔄 Renew Membership</Text>
        </TouchableOpacity>
      </View>
    </ScrollView>
  );
}

function InfoItem({ label, value }) {
  return (
    <View style={{ flex: 1, marginBottom: 8 }}>
      <Text style={{ color: "#888", fontSize: 11 }}>{label}</Text>
      <Text style={{ color: "#fff", fontSize: 14, fontWeight: "600" }}>{value}</Text>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e" },
  card: { backgroundColor: "#16213e", margin: 16, borderRadius: 16, padding: 20 },
  headerRow: { flexDirection: "row", alignItems: "center", marginBottom: 20 },
  bigAvatar: { width: 56, height: 56, borderRadius: 28, backgroundColor: "#e94560", alignItems: "center", justifyContent: "center" },
  bigAvatarText: { color: "#fff", fontSize: 24, fontWeight: "800" },
  name: { color: "#fff", fontSize: 20, fontWeight: "700" },
  phone: { color: "#aaa", fontSize: 13, marginTop: 2 },
  statusBadge: { marginTop: 6, fontSize: 12, fontWeight: "700", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, alignSelf: "flex-start" },
  active: { backgroundColor: "#4ecca322", color: "#4ecca3" },
  expired: { backgroundColor: "#e9456022", color: "#e94560" },
  infoRow: { flexDirection: "row" },
  section: { backgroundColor: "#16213e", marginHorizontal: 16, marginBottom: 12, borderRadius: 16, padding: 16 },
  sectionTitle: { color: "#aaa", fontSize: 13, fontWeight: "600", marginBottom: 12, textTransform: "uppercase" },
  btn: { backgroundColor: "#e94560", borderRadius: 10, padding: 14, alignItems: "center" },
  btnSecondary: { backgroundColor: "#0f3460" },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  assignMsg: { color: "#aaa", textAlign: "center", marginBottom: 10, fontSize: 13 },
});
