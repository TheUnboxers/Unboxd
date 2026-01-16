import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty";
import { Button } from "@/components/ui/button";
import { RefreshCcwIcon } from "lucide-react";
import { Spinner } from "@/components/ui/spinner";
import { BackendError, ExtendedStatus } from "@/hooks/recommendations";

export function StatusIndicator({status, backendError}: {status: ExtendedStatus, backendError: BackendError}) {
  const isUnexpectedError = backendError === BackendError.UNEXPECTED;
  const isUnclearError = backendError === BackendError.UNCLEAR_CAUSE_OF_FAILURE;
  const isError = backendError !== BackendError.NONE;

  const refreshPage = () => {
    window.location.reload(); 
  };

  return (
    <section className="py-24 relative overflow-hidden flex justify-center">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
        <Empty>
          <EmptyHeader>
            <EmptyTitle>
              {status} 
              {!isError && <Spinner className="ml-2 inline-block"/> }
            </EmptyTitle>

            <EmptyDescription>
              {isUnclearError && "If this seems off, please try again" }
              {isUnexpectedError && "Something went wrong, please try again" }
            </EmptyDescription>
          </EmptyHeader>

          {isError && 
            <EmptyContent>
                <Button variant="outline" size="sm" onClick={refreshPage}>
                <RefreshCcwIcon />
                Retry
              </Button>
            </EmptyContent>}
        </Empty>
      </div>
    </section>
  )
}
