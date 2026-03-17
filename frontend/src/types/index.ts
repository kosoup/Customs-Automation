export interface DeclarationItem {
  id?: number;
  declaration_id?: number;
  item_seq: number;
  product_name_ko?: string;
  product_name_en?: string;
  hscode?: string;
  model_spec?: string;
  quantity?: number;
  unit?: string;
  unit_price?: number;
  amount?: number;
}

export interface Declaration {
  id: number;
  status: string;
  created_at: string;
  updated_at: string;

  declarant_code?: string;
  declarant_name?: string;
  exporter_name?: string;
  exporter_business_number?: string;
  exporter_address?: string;
  buyer_name?: string;
  buyer_country_code?: string;
  buyer_address?: string;
  incoterms?: string;
  currency_code?: string;
  payment_method?: string;
  loading_port?: string;
  destination_country_code?: string;
  destination_port?: string;
  carrier?: string;
  shipping_date?: string;
  net_weight_kg?: number;
  gross_weight_kg?: number;
  package_type?: string;
  package_count?: number;
  invoice_number?: string;
  invoice_date?: string;
  total_amount?: number;
  submission_ref?: string;
  unipass_ref?: string;
  items: DeclarationItem[];
}

export interface DeclarationListItem {
  id: number;
  status: string;
  exporter_name?: string;
  buyer_name?: string;
  invoice_number?: string;
  total_amount?: number;
  currency_code?: string;
  created_at: string;
}

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}
