"use client"

import { Button } from "@/components/ui/button"
import { Menu, Globe, Sun, Moon, MessageSquare, Bell } from "lucide-react"
import { useState } from "react"

interface HeaderProps {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

export function Header({ sidebarOpen, setSidebarOpen }: HeaderProps) {
  const [isDark, setIsDark] = useState(true)
  const [language, setLanguage] = useState("EN")

  const toggleTheme = () => {
    setIsDark(!isDark)
    document.documentElement.classList.toggle("dark")
  }

  const toggleLanguage = () => {
    setLanguage(language === "EN" ? "中文" : "EN")
  }

  return (
    <header className="h-16 bg-card border-b border-border flex items-center justify-between px-6 sticky top-0 z-50">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="text-muted-foreground hover:text-foreground"
        >
          <Menu className="h-5 w-5" />
        </Button>

        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
            <svg viewBox="0 0 24 24" className="w-6 h-6 text-primary-foreground" fill="currentColor">
              <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 1L13.5 2.5L16.17 5.17L10.59 10.75C10.21 11.13 10.21 11.75 10.59 12.13L11.87 13.41C12.25 13.79 12.87 13.79 13.25 13.41L18.83 7.83L21.5 10.5L23 9H21ZM1 9H3L5.5 10.5L7.83 7.83L13.41 13.41C13.79 13.79 13.79 14.41 13.41 14.79L12.13 16.07C11.75 16.45 11.13 16.45 10.75 16.07L5.17 10.49L2.5 13.16L1 11.66V9Z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-foreground">Dragon Academy</h1>
            <p className="text-xs text-muted-foreground">Language & Cultural Institute</p>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLanguage}
          className="text-muted-foreground hover:text-foreground"
        >
          <Globe className="h-5 w-5" />
          <span className="sr-only">Toggle language</span>
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          className="text-muted-foreground hover:text-foreground"
        >
          {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          <span className="sr-only">Toggle theme</span>
        </Button>

        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground relative">
          <MessageSquare className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-primary rounded-full text-xs flex items-center justify-center text-primary-foreground">
            3
          </span>
          <span className="sr-only">Messages</span>
        </Button>

        <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground relative">
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-destructive rounded-full text-xs flex items-center justify-center text-destructive-foreground">
            5
          </span>
          <span className="sr-only">Notifications</span>
        </Button>
      </div>
    </header>
  )
}
