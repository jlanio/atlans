# executor/sync/validator.py
"""
SpatialValidator — validates the integrity of spatial datasets before upload.
"""
import logging

from executor.sync.scanner import Dataset

logger = logging.getLogger("executor.sync")


class ValidationResult:
    def __init__(self, valid: bool, warnings: list[str] | None = None, errors: list[str] | None = None):
        self.valid = valid
        self.warnings = warnings or []
        self.errors = errors or []


def validate_dataset(dataset: Dataset) -> ValidationResult:
    """
    Validates a spatial dataset.
    Returns a ValidationResult with valid=True/False and a list of warnings/errors.
    """
    warnings: list[str] = []
    errors: list[str] = []

    # 1. Shapefile completude
    if dataset.type == "shapefile" and not dataset.is_complete:
        errors.append(f"Shapefile '{dataset.name}' incompleto — faltam componentes obrigatorios (.shp/.dbf/.shx).")
        return ValidationResult(False, warnings, errors)

    # 2. File exists and is not empty
    for fname, finfo in dataset.files.items():
        if not finfo.path.exists():
            errors.append(f"Arquivo '{fname}' nao encontrado.")
        elif finfo.size == 0:
            errors.append(f"Arquivo '{fname}' esta vazio.")

    if errors:
        return ValidationResult(False, warnings, errors)

    # 3. Tenta abrir o arquivo principal
    primary = dataset.primary_path
    if not primary:
        errors.append("Nenhum arquivo principal encontrado no dataset.")
        return ValidationResult(False, warnings, errors)

    from executor.utils import classify_dataset_type
    data_type = classify_dataset_type(dataset.type)

    if data_type == "vector":
        try:
            import geopandas as gpd
            gdf = gpd.read_file(primary, rows=1)
            if gdf.empty:
                warnings.append(f"Dataset '{dataset.name}' esta vazio (0 features).")
            if gdf.crs is None:
                warnings.append(f"Dataset '{dataset.name}' sem CRS definido.")
        except Exception as e:
            errors.append(f"Falha ao abrir '{dataset.name}': {e}")
            return ValidationResult(False, warnings, errors)

    elif data_type == "raster":
        try:
            import rasterio
            with rasterio.open(primary) as src:
                if src.crs is None:
                    warnings.append(f"Raster '{dataset.name}' sem CRS definido.")
        except ImportError:
            warnings.append("rasterio nao instalado — validacao raster ignorada.")
        except Exception as e:
            errors.append(f"Falha ao abrir raster '{dataset.name}': {e}")
            return ValidationResult(False, warnings, errors)

    if warnings:
        for w in warnings:
            logger.warning("Validacao: %s", w)

    return ValidationResult(True, warnings, errors)


