import type { AxiosResponse } from "axios";

import { authApiClient } from "@/lib/api/client";

export type Review = {
  id: string;
  jobId: string;
  rating: number;
  title?: string;
  body?: string;
  helpfulVotes?: number;
  createdAt: string;
};

const LOCAL_REVIEWS_KEY = "agenticbay.jobReviews";

function readLocalReviews(): Record<string, Review> {
  if (typeof window === "undefined") {
    return {};
  }

  try {
    return JSON.parse(window.localStorage.getItem(LOCAL_REVIEWS_KEY) ?? "{}") as Record<
      string,
      Review
    >;
  } catch {
    return {};
  }
}

function writeLocalReview(jobId: string, review: Review) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    LOCAL_REVIEWS_KEY,
    JSON.stringify({
      ...readLocalReviews(),
      [jobId]: review,
    })
  );
}

export const reviewsApi = {
  async submit(
    jobId: string,
    data: { rating: number; title?: string; body?: string }
  ): Promise<AxiosResponse<Review>> {
    try {
      return await authApiClient.post(`/jobs/${jobId}/review`, data);
    } catch {
      const review: Review = {
        id: `local-review-${jobId}`,
        jobId,
        rating: data.rating,
        title: data.title,
        body: data.body,
        helpfulVotes: 0,
        createdAt: new Date().toISOString(),
      };
      writeLocalReview(jobId, review);
      return {
        data: review,
        status: 201,
        statusText: "Created",
        headers: {},
        config: {} as AxiosResponse["config"],
      };
    }
  },

  async getJobReview(jobId: string): Promise<AxiosResponse<Review | null>> {
    try {
      return await authApiClient.get(`/jobs/${jobId}/review`);
    } catch {
      return {
        data: readLocalReviews()[jobId] ?? null,
        status: 200,
        statusText: "OK",
        headers: {},
        config: {} as AxiosResponse["config"],
      };
    }
  },

  voteHelpful(reviewId: string): Promise<AxiosResponse<void>> {
    return authApiClient.post(`/reviews/${reviewId}/helpful`);
  },
};
