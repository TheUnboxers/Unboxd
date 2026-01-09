import { useState } from "react";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
  InputGroupButton,
} from "@/components/ui/input-group"
import { ModeToggle } from "@/components/theme-toggle"
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const navItems = [
  { href: "/", 
    label: "Home" },

  { href: "https://github.iu.edu/B365-Fall2025/Project-ez2-ermili-cch8-dvchavan", 
    label: "Docs", 
    isExternal: true },
]

export function NavBar({ username } : { username: string | null }) {
  const [user, setUser] = useState(username?.toString() || "");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
     router.push(`/recommendations?username=${user}`);
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/55 backdrop-blur-md">
      <div className="container mx-auto p-4 sm:px-6 lg:px-8 flex justify-between gap-4">
        {/* Right Side */}
        <div className="flex flex-wrap gap-y-4">
          { /* Navigation Links */ }
          {navItems.map((item) => (
            <Button key={item.href} variant="link" asChild>
              <Link href={item.href} target="_self" rel="noopener noreferrer">
                {item.label}
              </Link>
            </Button>
          ))}

          { /* Username Input */ }
          <form onSubmit={handleSubmit} className="pl-4 sm:min-w-sm sm:w-auto w-full">
            <InputGroup className="bg-accent/55 backdrop-blur-md">
              <InputGroupInput 
                className="w-full"
                id="username"
                type="text"
                placeholder="username"
                value={user}                
                onChange={(e) => setUser(e.target.value)} 
                autoComplete="off"/>
              <InputGroupAddon align="inline-end">
                <InputGroupButton
                  aria-label="Clear"
                  title="Clear"
                  size="icon-xs"
                  variant="link"
                  className="text-muted-foreground hover:text-foreground"
                  onClick={() => setUser("")}
                >
                  <X />
                </InputGroupButton>
              </InputGroupAddon>
            </InputGroup>
          </form>
          </div>

          {/* Left side */}
          { /* Theme Toggle */ }
          <ModeToggle />
        </div>
    </header>
  )
}