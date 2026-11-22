import React, { useEffect, useState, useCallback } from "react";
import {
  View, Text, TextInput, FlatList, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl,
} from "react-native";
import { getMembers } from "../api";
import { useNavigation, useFocusEffect } from "@react-navigation/native";

export default function MembersScreen() {
  const [members, setMembers] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const nav = useNavigation();

  const fetchMembers = async (q = "") => {
    try {
      const { data } = await getMembers(q);
      if (data.members) setMembers(data.members);
    } catch {}
    setLoading(false);
    setRefreshing(false);
  };

  useFocusEffect(useCallback(() => { fetchMembers(search); }, []));

  useEffect(() => {
    const t = setTimeout(() => fetchMembers(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const renderItem = ({ item }) => (
    <TouchableOpacity style={s.row} onPress={() => nav.navigate("MemberDetail", { member: item })}>
      <View style={[s.avatar, item.is_expired && s.expiredAvatar]}>
        <Text style={s.avatarText}>{item.name[0]}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={s.name}>{item.name}</Text>
        <Text style={s.phone}>{item.phone}</Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={[s.badge, item.is_expired ? s.badgeExpired : s.badgeActive]}>
          {item.is_expired ? "Expired" : "Active"}
        </Text>
        <Text style={s.plan}>{item.current_plan || "No plan"}</Text>
      </View>
    </TouchableOpacity>
  );

  if (loading) return <ActivityIndicator style={{ flex: 1 }} color="#e94560" />;

  return (
    <View style={s.root}>
      <TextInput
        style={s.search}
        placeholder="Search by name or phone..."
        placeholderTextColor="#888"
        value={search}
        onChangeText={setSearch}
      />
      <FlatList
        data={members}
        keyExtractor={i => String(i.id)}
        renderItem={renderItem}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchMembers(search); }} />}
        ListEmptyComponent={<Text style={s.empty}>No members found.</Text>}
      />
      <TouchableOpacity style={s.fab} onPress={() => nav.navigate("RegisterMember")}>
        <Text style={s.fabText}>+ Register</Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#1a1a2e", padding: 16 },
  search: { backgroundColor: "#0f3460", color: "#fff", borderRadius: 10, padding: 12, marginBottom: 12 },
  row: { flexDirection: "row", alignItems: "center", backgroundColor: "#16213e", borderRadius: 12, padding: 12, marginBottom: 8 },
  avatar: { width: 42, height: 42, borderRadius: 21, backgroundColor: "#e94560", alignItems: "center", justifyContent: "center", marginRight: 12 },
  expiredAvatar: { backgroundColor: "#555" },
  avatarText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  name: { color: "#fff", fontWeight: "600", fontSize: 15 },
  phone: { color: "#aaa", fontSize: 12 },
  badge: { fontSize: 11, fontWeight: "700", paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  badgeActive: { backgroundColor: "#0f346055", color: "#4ecca3" },
  badgeExpired: { backgroundColor: "#e9456022", color: "#e94560" },
  plan: { color: "#888", fontSize: 11, marginTop: 2 },
  empty: { color: "#aaa", textAlign: "center", marginTop: 40, fontSize: 15 },
  fab: { position: "absolute", bottom: 20, right: 20, backgroundColor: "#e94560", borderRadius: 30, paddingHorizontal: 24, paddingVertical: 14, elevation: 6 },
  fabText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});
