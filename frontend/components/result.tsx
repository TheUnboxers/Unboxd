import { ItemGroup } from "@/components/ui/item"
import { Movie } from "@/app/api/types.gen"
import { useState } from "react"
import YouTube, { YouTubeProps } from "react-youtube"
import { MovieCard } from "./movie-card"
import { CSVLink } from "react-csv"
import { Download, ThumbsUp, ThumbsDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/components/ui/toggle-group"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ResultProps {
  movies: Movie[];
}

export function Result({ movies, username }: ResultProps & { username: string }) {
  const [trailer, setTrailer] = useState<Movie | null>(null);
  const onPlayerReady: YouTubeProps['onReady'] = (event) => {
    // access to player in all event handlers via event.target
    event.target.pauseVideo();
  }

  const opts: YouTubeProps['opts'] = {
    height: '390',
    width: '640',
    playerVars: {
      // https://developers.google.com/youtube/player_parameters
      autoplay: 0,
    },
  };

  const headers = [
    { label: "imdbID", key: "movieId" },
  ];

  return (
    <>
      {/* Profile */}
      <section className="py-24 relative overflow-hidden bg-accent">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative flex justify-center items-center gap-8 ">
          <h3 className="scroll-m-20 text-2xl font-semibold tracking-tight text-center">
            {username}&apos;s movie recommendations
          </h3>
        </div>
      </section>


      {/* Trailer */}
      {trailer &&
        (
          <section className="py-24 relative overflow-hidden border-b-1">
            <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative flex flex-col justify-center items-center gap-8">
              <h4 className="scroll-m-20 text-xl font-semibold tracking-tight text-center">
                Now Playing: {trailer.name}
              </h4>
              <YouTube videoId={trailer.trailerID} opts={opts} onReady={onPlayerReady} />
            </div>
          </section>
        )}

      {/* Movies */}
      <section className="py-24 relative overflow-hidden">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative flex flex-col justify-center items-center gap-8">
          {/* Movie Cards */}
          <ItemGroup className="grid gap-4 grid-cols-[repeat(auto-fill,minmax(200px,1fr))]">
            {movies.map((movie) => (
              <MovieCard key={movie.name} {...movie} setTrailer={setTrailer} />
            ))}
          </ItemGroup>

          {/* Buttons */}
          <div className="flex flex-row flex-wrap gap-4">
            {/* Export buttons */}
            <CSVLink
              data={movies}
              headers={headers}
              filename={"letterboxd_import.csv"}>
              <Button variant="outline"><Download /> DOWNLOAD RECOMMENDATIONS</Button>
            </CSVLink>

            {/* Like buttons */}
            <Tooltip>
              <TooltipTrigger asChild>
                <ToggleGroup type="single" variant="outline">
                  <ToggleGroupItem value="like" aria-label="Toggle like">
                    <ThumbsUp />
                  </ToggleGroupItem>
                  <ToggleGroupItem value="dislike" aria-label="Toggle dislike">
                    <ThumbsDown />
                  </ToggleGroupItem>
                </ToggleGroup>
              </TooltipTrigger>
              <TooltipContent>
                <p>Rate recommendation</p>
              </TooltipContent>
            </Tooltip>

          </div>
        </div>
      </section>
    </>
  );
}