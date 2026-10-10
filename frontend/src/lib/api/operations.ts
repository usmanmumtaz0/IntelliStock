import { apiRequest } from "./client";
import type { InventoryDto, UserRole } from "./types";

export interface ProductInput {
  sku: string;
  name: string;
  description: string | null;
  low_stock_threshold: number;
  reorder_point: number;
}
export interface ProductDto extends ProductInput {
  id: string;
}
export interface AccountDto {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  signup_pending: boolean;
}
export interface ZoneInput {
  camera_id: string;
  name: string;
  description: string | null;
  polygon: [number, number][];
  detection_confidence_threshold: number;
  products: { class_id: number; product_id: string; allow_empty: boolean }[];
}
export interface ZoneConfiguration extends ZoneInput {
  id: string;
  restart_required: boolean;
}

export const operations = {
  products: () => apiRequest<ProductDto[]>("/products"),
  saveProduct: (input: ProductInput, id?: string) => {
    const { sku, ...update } = input;
    return apiRequest<ProductDto>(id ? `/products/${encodeURIComponent(id)}` : "/products", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(id ? update : { sku, ...update }),
    });
  },
  accounts: () => apiRequest<AccountDto[]>("/users"),
  approveSignup: (id: string) =>
    apiRequest<AccountDto>(`/users/${encodeURIComponent(id)}/approve`, { method: "POST" }),
  createAccount: (input: { email: string; username: string; password: string; role: UserRole }) =>
    apiRequest<AccountDto>("/users", { method: "POST", body: JSON.stringify(input) }),
  updateAccount: (id: string, input: { role: UserRole; is_active: boolean }) =>
    apiRequest<AccountDto>(`/users/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(input),
    }),
  zoneConfiguration: (id: string) =>
    apiRequest<ZoneConfiguration>(`/zones/${encodeURIComponent(id)}/configuration`),
  saveZone: (input: ZoneInput, id?: string) =>
    apiRequest<ZoneConfiguration>(id ? `/zones/${encodeURIComponent(id)}` : "/zones", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(input),
    }),
  correctInventory: (
    id: string,
    input: { quantity: number; reason: string; expected_updated_at: string },
  ) =>
    apiRequest<InventoryDto>(`/inventory/${encodeURIComponent(id)}/corrections`, {
      method: "POST",
      body: JSON.stringify(input),
    }),
};
