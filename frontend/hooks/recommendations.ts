"use client";

import { useEffect, useState } from "react";
import api from "@/app/api";
import { Status } from "@/app/api/types.gen";
import { AxiosError, HttpStatusCode } from "axios";

export enum BackendError {
    NONE = "None",
    UNEXPECTED = "Unexpected",
    UNCLEAR_CAUSE_OF_FAILURE = "Unclear cause of failure",
    IMPOSSIBLE_REQUEST = "Impossible request",
}

export type ExtendedStatus = Status | "Error" | "404 Not Found";

function useRecommendations(username: string | null) {
    const [movies, setMovies] = useState([]);
    const [status, setStatus] = useState<ExtendedStatus>(Status.STARTING);
    const [backendError, setBackendError] = useState<BackendError>(BackendError.NONE);

    // Fetches movies, assuming the recommendation process is finished
    const fetchMovies = async () => {
        try {
            const res = await api.get(`/movies/?username=${username}`);
            setMovies(res.data);
            console.log("Movies:", res.data);
        }
        catch (error) {
            setStatus("Error");
            setBackendError(BackendError.UNEXPECTED);
            console.log(error);
        }
    };

    // Fetches status
    const getStatus = async (intervalId: NodeJS.Timeout) => {
        try {
            const response = await api.get('/status/', { params: { username } });
            const newStatus = response.data;
            setStatus(newStatus);
            console.log("Status:", newStatus);

            if (newStatus == Status.FINISHED) {
                clearInterval(intervalId);
                fetchMovies();
            }
        }
        catch (error) {
            console.log(error);
            clearInterval(intervalId);

            // Handle unexpected error
            if (!(error instanceof AxiosError) || error.response === undefined) {
                setStatus("Error");
                setBackendError(BackendError.UNEXPECTED);
                return;
            }

            // Handle known errors from backend
            setStatus(error.response.data.detail);
            if (error.status == HttpStatusCode.NotFound) {
                setBackendError(BackendError.UNCLEAR_CAUSE_OF_FAILURE);
            } else if (error.status == HttpStatusCode.InternalServerError) {
                setBackendError(BackendError.IMPOSSIBLE_REQUEST);
            } else {
                setBackendError(BackendError.UNEXPECTED);
            }
        }
    };

    // On page load
    useEffect(() => {
        console.log("Fetch recommendations for:", username);

        if (!username) {
            console.log("No username provided");
            setStatus("404 Not Found");
            setBackendError(BackendError.IMPOSSIBLE_REQUEST);
            return;
        }

        // Reset UI immediately when username changes
        setMovies([]);
        setStatus(Status.STARTING);
        setBackendError(BackendError.NONE);

        let intervalId: NodeJS.Timeout | null = null;

        async function start() {
            try {
                await api.post('/usernames/', { username: username });
                intervalId = setInterval(() => {
                    getStatus(intervalId!);
                }, 1000);
            }
            catch (error) {
                console.log(error);
                setStatus("Error");
                setBackendError(BackendError.UNEXPECTED);
            }
        }

        start();

        // CLEANUP: stop old interval when username changes
        return () => {
            if (intervalId) clearInterval(intervalId);
        };

    }, [username]);

    return { movies, status, backendError };
}

export { useRecommendations };