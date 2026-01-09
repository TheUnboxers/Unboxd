"use client"

import { useSearchParams } from "next/navigation";
import { NavBar } from "@/components/nav-bar";
import { Result } from "@/components/result";
import { StatusIndicator } from "@/components/status-indicator";
import { Status } from "@/app/api/types.gen";
import { useRecommendations } from "@/hooks/recommendations";

export default function RecommendationsPage() {
  const searchParams = useSearchParams();
  const username  = searchParams.get("username");

  const { movies, status, backendError } = useRecommendations(username);

  return (
    <div className="min-h-screen w-full bg-background flex flex-col">
      <NavBar username={username} />

      {status === Status.FINISHED && username && <Result movies={movies} username={username} />}
      {status !== Status.FINISHED && <StatusIndicator status={status} backendError={backendError} />}
    
    </div>
  );
}
