"use client";

import { useState } from "react";

import { agentsApi, type ValidationResult } from "@/lib/api/agents";

export function useAgentValidation() {
  const [isValidating, setIsValidating] = useState(false);
  const [result, setResult] = useState<ValidationResult | null>(null);
  const [error, setError] = useState<unknown>(null);

  const validate = async (baseUrl: string) => {
    setIsValidating(true);
    setError(null);

    try {
      const { data } = await agentsApi.validate(baseUrl);
      setResult(data);
      return data;
    } catch (validationError) {
      setError(validationError);
      throw validationError;
    } finally {
      setIsValidating(false);
    }
  };

  return { validate, isValidating, result, error };
}
