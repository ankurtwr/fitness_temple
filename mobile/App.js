import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { Text } from "react-native";

import { AuthProvider, useAuth } from "./src/context/AuthContext";
import LoginScreen from "./src/screens/LoginScreen";
import AttendanceScreen from "./src/screens/AttendanceScreen";
import MembersScreen from "./src/screens/MembersScreen";
import MemberDetailScreen from "./src/screens/MemberDetailScreen";
import RegisterMemberScreen from "./src/screens/RegisterMemberScreen";
import RenewMembershipScreen from "./src/screens/RenewMembershipScreen";

const Tab = createBottomTabNavigator();
const Stack = createNativeStackNavigator();

function MembersStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: { backgroundColor: "#16213e" },
        headerTintColor: "#fff",
        headerTitleStyle: { fontWeight: "700" },
      }}
    >
      <Stack.Screen name="MembersList" component={MembersScreen} options={{ title: "Members" }} />
      <Stack.Screen name="MemberDetail" component={MemberDetailScreen} options={{ title: "Member Profile" }} />
      <Stack.Screen name="RegisterMember" component={RegisterMemberScreen} options={{ title: "Register Member" }} />
      <Stack.Screen name="RenewMembership" component={RenewMembershipScreen} options={{ title: "Renew Membership" }} />
    </Stack.Navigator>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: { backgroundColor: "#16213e", borderTopColor: "#0f3460" },
        tabBarActiveTintColor: "#e94560",
        tabBarInactiveTintColor: "#888",
      }}
    >
      <Tab.Screen
        name="Attendance"
        component={AttendanceScreen}
        options={{
          tabBarIcon: () => <Text style={{ fontSize: 20 }}>📋</Text>,
          headerShown: true,
          headerStyle: { backgroundColor: "#16213e" },
          headerTintColor: "#fff",
          headerTitleStyle: { fontWeight: "700" },
          title: "Attendance",
        }}
      />
      <Tab.Screen
        name="Members"
        component={MembersStack}
        options={{ tabBarIcon: () => <Text style={{ fontSize: 20 }}>👥</Text> }}
      />
    </Tab.Navigator>
  );
}

function AppContent() {
  const { user } = useAuth();
  return (
    <NavigationContainer>
      {user ? <MainTabs /> : <LoginScreen />}
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
