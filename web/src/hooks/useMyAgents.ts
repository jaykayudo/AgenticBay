"use client";

import useSWR from "swr";

import { agentsApi, type AgentStatus } from "@/lib/api/agents";

export function useMyAgents() {
  const { data, error, isLoading, mutate } = useSWR("/agents/mine", () =>
    agentsApi.myAgents().then((response) => response.data.agents)
  );

  async function setStatus(agentId: string, status: Extract<AgentStatus, "ACTIVE" | "PAUSED">) {
    await mutate(
      async (current = []) => {
        const { data: updatedAgent } = await agentsApi.setStatus(agentId, status);
        return current.map((agent) => (agent.id === agentId ? updatedAgent : agent));
      },
      {
        optimisticData: (current = []) =>
          current.map((agent) => (agent.id === agentId ? { ...agent, status } : agent)),
        rollbackOnError: true,
        revalidate: true,
      }
    );
  }

  async function deleteAgent(agentId: string) {
    await mutate(
      async (current = []) => {
        await agentsApi.delete(agentId);
        return current.filter((agent) => agent.id !== agentId);
      },
      {
        optimisticData: (current = []) => current.filter((agent) => agent.id !== agentId),
        rollbackOnError: true,
        revalidate: true,
      }
    );
  }

  return {
    agents: data ?? [],
    error,
    isLoading,
    refresh: mutate,
    setStatus,
    deleteAgent,
  };
}
