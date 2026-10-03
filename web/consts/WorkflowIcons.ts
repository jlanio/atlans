import { IconType } from "react-icons";
import { BsFiletypeJson, BsFiletypeCsv, BsSymmetryVertical } from "react-icons/bs";
import {
  LuCircleDotDashed, LuFileArchive, LuFileOutput, LuLayers3,
  LuTimerReset, LuFile
} from "react-icons/lu";
import {
  MdAdjust, MdGrid4X4, MdHttp, MdWebhook, MdPublic,
  MdOutlineEmail, MdCloudUpload, MdBlurOn, MdCallMerge, MdLoop
} from "react-icons/md";
import { FiDatabase, FiEdit, FiFilter } from "react-icons/fi";
import { FaSatellite } from "react-icons/fa";
import { SiPostgresql } from "react-icons/si";
import { PiBoundingBoxBold, PiIntersect, PiIntersectSquareDuotone } from "react-icons/pi";
import {
  TbArrowsSplit2, TbLayersDifference, TbLayersUnion, TbZoomInArea,
  TbScissors, TbShieldCheck, TbVectorTriangle, TbLayersIntersect,
  TbGridDots, TbTemperaturePlus, TbSum,
  TbBraces, TbGitMerge, TbRefresh, TbArrowUpRight, TbMapPin,
  TbLogin2, TbLogout2,
  TbFileCode, TbWorldDownload, TbBrandPython,
  TbSwitchHorizontal, TbSortAscending, TbCopyOff, TbDatabaseImport,
  TbWebhook, TbVersionsFilled, TbCategory, TbTableShare,
  TbMap2,
} from "react-icons/tb";
import { IoNotificationsOutline } from "react-icons/io5";
import { GrTrigger, GrAction } from "react-icons/gr";

export type NodeTypes = "trigger" | "action" | "control" | "datasource" | "output" | "spatial"

export const NODE_TYPES = {
  "action": GrAction,
  "control": IoNotificationsOutline,
  "trigger": GrTrigger,
  "datasource": FiDatabase,
  "output": LuFileOutput,
  "spatial": FaSatellite
} as Record<NodeTypes | string, IconType>

// ── Triggers ────────────────────────────────────────────────────────────────
export type TriggersType =
  | "FileTrigger"
  | "WebhookTrigger"
  | "ScheduleTrigger"
  | "GeofenceTrigger"
  | "SubWorkflowInput"

export const TRIGGER_ICONS = {
  "FileTrigger":      LuFileArchive,
  "WebhookTrigger":   MdWebhook,
  "ScheduleTrigger":  LuTimerReset,
  "GeofenceTrigger":  TbMapPin,
  "SubWorkflowInput": TbLogin2,
} satisfies Record<TriggersType, IconType>

// ── Actions ──────────────────────────────────────────────────────────────────
export type ActionsType =
  | "AttributeFilter"
  | "AttributeJoin"
  | "HttpRequest"
  | "SetFields"
  | "OverlapPercentage"
  | "GeocodeNode"
  | "PythonScript"
  | "Sort"
  | "RemoveDuplicates"

export const ACTION_ICONS = {
  "AttributeFilter":   FiFilter,
  "AttributeJoin":     TbTableShare,
  "HttpRequest":       MdHttp,
  "SetFields":         FiEdit,
  "OverlapPercentage": PiIntersect,
  "GeocodeNode":       MdPublic,
  "PythonScript":      TbBrandPython,
  "Sort":              TbSortAscending,
  "RemoveDuplicates":  TbCopyOff,
} satisfies Record<ActionsType, IconType>

// ── Spatial ──────────────────────────────────────────────────────────────────
export type SpatialType =
  | "IntersectionNode"
  | "Buffer"
  | "ComputeArea"
  | "CentroidNode"
  | "DifferenceNode"
  | "SymmetricDifferenceNode"
  | "TransformCRS"
  | "ComputeBoundingBox"
  | "UnionNode"
  | "Clip"
  | "ValidateGeometry"
  | "Simplify"
  | "Dissolve"
  | "SpatialJoin"
  | "Heatmap"
  | "Partition"
  | "Aggregate"
  | "VoronoiNode"
  | "ConvexHullNode"
  | "SpatialFilterNode"
  | "FilterByGeometryType"

export const SPATIAL_ICONS = {
  "IntersectionNode":       PiIntersectSquareDuotone,
  "Buffer":                 LuCircleDotDashed,
  "CentroidNode":           MdAdjust,
  "TransformCRS":           MdGrid4X4,
  "ComputeArea":            TbZoomInArea,
  "DifferenceNode":         TbLayersDifference,
  "SymmetricDifferenceNode": BsSymmetryVertical,
  "ComputeBoundingBox":     PiBoundingBoxBold,
  "UnionNode":              TbLayersUnion,
  "Clip":                   TbScissors,
  "ValidateGeometry":       TbShieldCheck,
  "Simplify":               TbVectorTriangle,
  "Dissolve":               MdBlurOn,
  "SpatialJoin":            TbLayersIntersect,
  "Heatmap":                TbTemperaturePlus,
  "Partition":              TbGridDots,
  "Aggregate":              TbSum,
  "VoronoiNode":          MdCallMerge,
  "ConvexHullNode":       MdLoop,
  "SpatialFilterNode":    FiFilter,
  "FilterByGeometryType": TbCategory,
} satisfies Record<SpatialType, IconType>

// ── Outputs ───────────────────────────────────────────────────────────────────
export type OutputType =
  | "SaveToPostGIS"
  | "SaveToPostgres"
  | "SaveGeoJSON"
  | "SaveToShapefile"
  | "SaveToGeoParquet"
  | "SaveToS3"
  | "SendEmail"
  | "SendWebhook"
  | "DataOutput"
  | "Response"
  | "PublishMap"
  | "CartaImagem"
  | "SubWorkflowOutput"

export const OUTPUT_ICONS = {
  "SaveGeoJSON":       BsFiletypeJson,
  "SaveToPostGIS":     SiPostgresql,
  "SaveToPostgres":    SiPostgresql,
  "SaveToShapefile":   LuFileArchive,
  "SaveToGeoParquet":  LuFile,
  "SaveToS3":          MdCloudUpload,
  "SendEmail":         MdOutlineEmail,
  "SendWebhook":       MdWebhook,
  "DataOutput":        LuFileOutput,
  "Response":          TbWebhook,
  "PublishMap":        MdPublic,
  "CartaImagem":       TbMap2,
  "SubWorkflowOutput": TbLogout2,
} satisfies Record<OutputType, IconType>

// ── DataSources ───────────────────────────────────────────────────────────────
export type DataSourceType =
  | "DatabaseSpatialQuery"
  | "DatabaseQuery"
  | "ReadGeoJSON"
  | "ReadShapefile"
  | "ReadGeoParquet"
  | "ReadCSVWithCoords"
  | "WFS"
  | "DataInput"

export const DATASOURCE_ICONS = {
  "DatabaseQuery":        FiDatabase,
  "DatabaseSpatialQuery": LuLayers3,
  "ReadGeoJSON":          BsFiletypeJson,
  "ReadShapefile":        LuFileArchive,
  "ReadGeoParquet":       TbFileCode,
  "ReadCSVWithCoords":    BsFiletypeCsv,
  "WFS":                  TbWorldDownload,
  "DataInput":            TbDatabaseImport,
} satisfies Record<DataSourceType, IconType>

// ── Controls ──────────────────────────────────────────────────────────────────
export type ControlsType =
  | "Conditional"
  | "JinjaBranch"
  | "Merge"
  | "Loop"
  | "SubWorkflow"
  | "Switch"
  | "ChangeDetector"

export const CONTROL_ICONS = {
  "Conditional":    TbArrowsSplit2,
  // New control nodes
  "JinjaBranch":    TbBraces,
  "Merge":          TbGitMerge,
  "Loop":           TbRefresh,
  "SubWorkflow":    TbArrowUpRight,
  "Switch":         TbSwitchHorizontal,
  "ChangeDetector": TbVersionsFilled,
} satisfies Record<ControlsType, IconType>

// ── Unified map for the drawer ────────────────────────────────────────────────
export const NODE_ICONS = {
  ...TRIGGER_ICONS,
  ...ACTION_ICONS,
  ...DATASOURCE_ICONS,
  ...CONTROL_ICONS,
  ...SPATIAL_ICONS,
  ...OUTPUT_ICONS,
} as Record<string, IconType>;
