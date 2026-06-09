/**
 * Slice Of Pi — TypeScript Interface Contracts
 *
 * Frontend and MCP server interfaces that define the UI plugin system,
 * dashboard widget contracts, MCP tool registry, and transport layer.
 *
 * These interfaces are the TypeScript counterpart to the Python ABCs.
 * Implementations live in the frontend (Vue/React) and MCP server packages.
 */

// ============================================================================
// Component reference type (avoid framework coupling)
// ============================================================================

/** Opaque component reference — resolved by the hosting framework. */
type Component = unknown;

/** Pinia/Vuex/Zustand store reference. */
type Store = unknown;

/** Vue Router / React Router reference. */
type Router = unknown;

// ============================================================================
// UI Plugin System
// ============================================================================

/** Configuration for a settings tab registered by a plugin. */
export interface SettingsTab {
  id: string;
  label: string;
  icon?: string;
  component: Component;
  /** Tab badge (e.g., "NEW", count). */
  badge?: string | number;
}

/** Configuration for a dashboard widget registered by a plugin. */
export interface DashboardWidget {
  id: string;
  title: string;
  component: Component;
  defaultSize: { w: number; h: number };
  minSize: { w: number; h: number };
  /** Refresh interval in milliseconds (0 = no auto-refresh). */
  refreshInterval?: number;
}

/** Configuration for an agent action button registered by a plugin. */
export interface AgentAction {
  id: string;
  label: string;
  icon?: string;
  /** Called when the action button is clicked. */
  handler: (agentId: string) => Promise<void> | void;
  /** Show only for agents matching these conditions. */
  conditions?: {
    status?: string[];
    hasCapability?: string[];
  };
}

/** Context passed to plugins during initialization. */
export interface PluginContext {
  apiClient: ApiClient;
  eventBus: EventBus;
  store: Store;
}

/**
 * UI Plugin — registers custom views, settings tabs, dashboard widgets,
 * and agent action buttons.
 *
 * One plugin per extension. Plugins are loaded at application startup
 * and their components are merged into the main UI.
 */
export interface UIPlugin {
  id: string;
  name: string;
  version: string;

  /** Register custom routes (views). */
  registerRoutes(router: Router): void;

  /** Register custom settings tabs. */
  registerSettingsTabs(): SettingsTab[];

  /** Register custom dashboard widgets. */
  registerWidgets(): DashboardWidget[];

  /** Register custom agent action buttons. */
  registerAgentActions(): AgentAction[];

  /** Initialize the plugin. Called once at startup. */
  init(context: PluginContext): Promise<void>;
}

// ============================================================================
// MCP Transport
// ============================================================================

/** JSON Schema type (simplified). */
type JSONSchema = Record<string, unknown>;

/** Incoming MCP request. */
export interface MCPRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

/** Outgoing MCP response. */
export interface MCPResponse {
  jsonrpc: "2.0";
  id: string | number;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/** Result of executing a tool. */
export interface ToolResult {
  content: Array<{
    type: "text" | "image" | "resource";
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
  isError?: boolean;
}

/** Definition of a single tool. */
export interface ToolDefinition {
  name: string;
  description: string;
  inputSchema: JSONSchema;
  handler: (params: unknown) => Promise<ToolResult>;
}

/**
 * Tool Registry — manages the set of tools exposed by the MCP server.
 * Tools can be registered/unregistered dynamically, and the registry
 * handles discovery and execution.
 */
export interface ToolRegistry {
  /** Register a new tool dynamically. */
  register(tool: ToolDefinition): void;

  /** Unregister a tool by name. */
  unregister(toolName: string): void;

  /** List all registered tools with their metadata. */
  list(): ToolDefinition[];

  /** Execute a tool by name with parameters. */
  execute(toolName: string, params: unknown): Promise<ToolResult>;

  /** List tool names matching a prefix (for auto-complete). */
  search?(prefix: string): string[];

  /** Get detailed schema for a single tool. */
  get?(toolName: string): ToolDefinition | undefined;
}

/**
 * MCP Transport — abstracts the communication protocol between
 * MCP client and server. Supports stdio, SSE, WebSocket, and
 * custom transports.
 */
export interface MCPTransport {
  /** Start the transport and begin listening for requests. */
  start(): Promise<void>;

  /** Register a handler for incoming requests. */
  onRequest(handler: (request: MCPRequest) => Promise<MCPResponse>): void;

  /** Send a notification (fire-and-forget, no response expected). */
  notify(method: string, params: unknown): Promise<void>;

  /** Gracefully shut down the transport. */
  stop(): Promise<void>;

  /** Return transport metadata (type, capabilities). */
  metadata?(): {
    type: "stdio" | "sse" | "websocket" | "custom";
    version: string;
    capabilities: string[];
  };
}

// ============================================================================
// Client Types (for PluginContext)
// ============================================================================

/** HTTP client for the backend API. */
export interface ApiClient {
  get<T = unknown>(path: string, params?: Record<string, string>): Promise<T>;
  post<T = unknown>(path: string, body?: unknown): Promise<T>;
  put<T = unknown>(path: string, body?: unknown): Promise<T>;
  delete<T = unknown>(path: string): Promise<T>;
}

/** Event bus for real-time updates in the frontend. */
export interface EventBus {
  on(event: string, handler: (data: unknown) => void): void;
  off(event: string, handler: (data: unknown) => void): void;
  emit(event: string, data: unknown): void;
}
