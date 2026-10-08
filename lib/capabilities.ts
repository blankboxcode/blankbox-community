export const capabilityNames = [
  'library',
  'localPlayback',
  'localMetadata',
  'physicalCollection',
  'preorders',
  'managedImports',
  'verifiedBackups',
  'jellyfinCatalog',
  'plexCatalog',
  'ownerProfile',
  'immichCatalog',
  'storageHealth',
  'multiUser',
] as const;

export type CapabilityName = (typeof capabilityNames)[number];
export type Capability = {
  supported: boolean;
  configured?: boolean;
  reason?: string;
  modelVersion?: number;
  directPlay?: boolean;
  transcoding?: boolean;
};

export type BlankBoxCapabilities = {
  apiVersion: 1;
  productVersion: string;
  catalogSchemaVersion: number | null;
  mode: 'box';
  features: Record<CapabilityName, Capability>;
};
