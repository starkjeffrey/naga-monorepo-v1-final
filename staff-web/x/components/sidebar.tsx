"use client"

import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  GraduationCap,
  Users,
  BookOpen,
  Calendar,
  FileText,
  BarChart3,
  Settings,
  Globe,
  Award,
  UserCheck,
  ClipboardList,
  Building,
  CreditCard,
  MessageCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface SidebarProps {
  isOpen: boolean
}

const menuItems = [
  {
    title: "Academic Affairs",
    items: [
      { icon: GraduationCap, label: "Student Management", active: true },
      { icon: BookOpen, label: "Course Catalog" },
      { icon: Calendar, label: "Class Scheduling" },
      { icon: Award, label: "Certifications" },
    ],
  },
  {
    title: "Language Testing",
    items: [
      { icon: FileText, label: "Test Administration" },
      { icon: UserCheck, label: "Examiner Portal" },
      { icon: ClipboardList, label: "Results Management" },
      { icon: BarChart3, label: "Performance Analytics" },
    ],
  },
  {
    title: "Administration",
    items: [
      { icon: Building, label: "Facility Management" },
      { icon: CreditCard, label: "Financial Services" },
      { icon: MessageCircle, label: "Communications" },
      { icon: Users, label: "Staff Directory" },
    ],
  },
  {
    title: "International",
    items: [
      { icon: Globe, label: "Exchange Programs" },
      { icon: FileText, label: "Visa Services" },
      { icon: Users, label: "Partner Institutions" },
    ],
  },
]

export function Sidebar({ isOpen }: SidebarProps) {
  return (
    <aside
      className={cn(
        "fixed left-0 top-16 h-[calc(100vh-4rem)] bg-sidebar border-r border-sidebar-border transition-all duration-300 z-40",
        isOpen ? "w-64" : "w-16",
      )}
    >
      <ScrollArea className="h-full">
        <div className="p-4 space-y-6">
          {menuItems.map((section, sectionIndex) => (
            <div key={sectionIndex} className="space-y-2">
              {isOpen && (
                <h3 className="text-xs font-semibold text-sidebar-foreground/60 uppercase tracking-wider px-2">
                  {section.title}
                </h3>
              )}
              <div className="space-y-1">
                {section.items.map((item, itemIndex) => (
                  <Button
                    key={itemIndex}
                    variant={item.active ? "default" : "ghost"}
                    className={cn(
                      "w-full justify-start gap-3 h-10",
                      !isOpen && "justify-center px-2",
                      item.active
                        ? "bg-sidebar-primary text-sidebar-primary-foreground hover:bg-sidebar-primary/90"
                        : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    )}
                  >
                    <item.icon className="h-4 w-4 flex-shrink-0" />
                    {isOpen && <span className="text-sm">{item.label}</span>}
                  </Button>
                ))}
              </div>
            </div>
          ))}

          {isOpen && (
            <div className="pt-4 border-t border-sidebar-border">
              <Button
                variant="ghost"
                className="w-full justify-start gap-3 h-10 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
              >
                <Settings className="h-4 w-4" />
                <span className="text-sm">Settings</span>
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </aside>
  )
}
