import type { ZoneScore } from "../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`);
  }
  return res.json();
}

export async function getZones(): Promise<ZoneScore[]> {
  const res = await fetch(`${API_BASE_URL}/zones`);
  if (!res.ok) {
    throw new Error(`Failed to fetch zones: ${res.status}`);
  }
  return res.json();
}

export async function getZoneEvents(id: string): Promise<string[]> {
  const res = await fetch(`${API_BASE_URL}/zones/${encodeURIComponent(id)}/events`);
  if (!res.ok) {
    throw new Error(`Failed to fetch events for ${id}: ${res.status}`);
  }
  return res.json();
}
