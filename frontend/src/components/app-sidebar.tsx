import { Link, useLocation } from "react-router-dom"
import { Building2, BookOpen, Home, LogOut, FileText, FolderOpen } from "lucide-react"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useAuth } from "@/hooks/useAuth"

const menuItems = [
  {
    title: "ワークフロー",
    url: "/sessions",
    icon: FileText,
  },
  {
    title: "金融機関・アンケート管理",
    url: "/banks",
    icon: Building2,
  },
  {
    title: "共通回答DB管理",
    url: "/common-answers",
    icon: BookOpen,
  },
  {
    title: "システム別ナレッジDB管理",
    url: "/kb-folders",
    icon: FolderOpen,
  },
]

export function AppSidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <Sidebar>
      <SidebarHeader className="border-b border-sidebar-border">
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold">
            I
          </div>
          <div className="flex flex-col">
            <span className="font-semibold text-base leading-tight">FISC-QAv2</span>
            <span className="text-xs text-sidebar-foreground/70">PoC雛形環境</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Menu</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === item.url}
                    tooltip={item.title}
                  >
                    <Link to={item.url}>
                      <item.icon />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="border-t border-sidebar-border">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={logout}>
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs">
                {user?.last_name?.charAt(0) || "U"}
              </div>
              <span className="truncate">{user?.last_name} {user?.first_name}</span>
              <LogOut className="ml-auto h-4 w-4" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  )
}
