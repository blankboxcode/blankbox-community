import type { Kind } from './media';

export type PreorderStatus = 'ordered' | 'shipped' | 'part-received' | 'received' | 'cancelled';
export type PreorderDraft = {
  releaseType?: 'physical' | 'digital'; digitalPlatform?: string; digitalFormat?: string; digitalUrl?: string;
  title: string; kind: Kind; year: number | null; format: string; edition: string; season: string | null;
  label: string; vendor: string; quantity: number; price: string; currency: string;
  dateOrdered: string; releaseDate: string; expectedDeliveryDate: string; trackingNumber: string;
  orderNumber: string; notes: string; platform: string; region: string; barcode: string;
  deliveryStatus: 'ordered' | 'shipped' | 'cancelled';
};
export type Preorder = PreorderDraft & {
  id: string; revision: number; receivedQuantity: number; status: PreorderStatus;
  createdAt: string; updatedAt: string; intentionId?: string;
  intentionReference?: { workId: string | null; releaseId: string | null; identifier?: { namespace: string; value: string } };
};
export type PreorderReceipt = {
  id: string; preorderId: string; itemId: string; currentItemId?: string | null;
  releaseType?: 'physical' | 'digital'; receivedDetails?: {format: string; platform: string; location: string; edition: string};
  quantity: number; receivedAt: string; createdAt: string; sourceIds: string[]; copyIds: string[]; purchaseRecordIds?: string[];
  orderDetails: Pick<PreorderDraft, 'title' | 'kind' | 'year' | 'format' | 'edition' | 'season' | 'label' | 'vendor' | 'price' | 'currency' | 'dateOrdered' | 'orderNumber' | 'trackingNumber' | 'notes' | 'releaseDate' | 'expectedDeliveryDate' | 'platform' | 'region' | 'barcode'>;
};
export type PreorderPage = { preorders: Preorder[]; total: number; offset: number; limit: number; counts: { active: number; received: number; cancelled: number } };
export type PreorderDetail = { preorder: Preorder; receipts: PreorderReceipt[] };
export const preorderStatusNames: Record<PreorderStatus, string> = {
  ordered: 'Ordered', shipped: 'Shipped', 'part-received': 'Part received', received: 'Received', cancelled: 'Cancelled',
};
export function emptyPreorder(): PreorderDraft {
  return { releaseType: 'physical', digitalPlatform: '', digitalFormat: '', digitalUrl: '', title: '', kind: 'movie', year: null, format: 'Blu-ray', edition: '', season: null,
    label: '', vendor: '', quantity: 1, price: '', currency: 'USD', dateOrdered: '', releaseDate: '',
    expectedDeliveryDate: '', trackingNumber: '', orderNumber: '', notes: '', platform: '', region: '', barcode: '', deliveryStatus: 'ordered' };
}
