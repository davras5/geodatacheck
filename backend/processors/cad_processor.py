"""
CAD/DWG Processor for CAFM Basisplan validation.

Validates DWG/DXF files against BBL CAFM Basisplan requirements.

Note: For DWG files, this module requires either:
1. ODA File Converter (free) to convert DWG to DXF
2. Direct DXF upload

The ezdxf library is used for reading DXF files.
"""

import io
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math

try:
    import ezdxf
    from ezdxf.entities import LWPolyline, Insert, Text, MText
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CADValidationError:
    """Represents a validation error in a CAD file."""
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    layer: Optional[str] = None
    entity_handle: Optional[str] = None
    location: Optional[Tuple[float, float]] = None

    def to_dict(self) -> dict:
        return {
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'severity': self.severity.value,
            'message': self.message,
            'layer': self.layer,
            'entity_handle': self.entity_handle,
            'location': self.location,
        }


@dataclass
class CADValidationResult:
    """Complete result of a CAD validation run."""
    filename: str
    errors: List[CADValidationError] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    layers_found: List[str] = field(default_factory=list)
    room_count: int = 0
    total_area: float = 0.0

    @property
    def error_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for e in self.errors if e.severity == Severity.WARNING)

    @property
    def is_valid(self) -> bool:
        return self.error_count == 0

    def to_dict(self) -> dict:
        return {
            'filename': self.filename,
            'is_valid': self.is_valid,
            'error_count': self.error_count,
            'warning_count': self.warning_count,
            'errors': [e.to_dict() for e in self.errors],
            'statistics': self.statistics,
            'layers_found': self.layers_found,
            'room_count': self.room_count,
            'total_area': round(self.total_area, 2),
        }


# BBL Layer Standards
BBL_REQUIRED_LAYERS = {
    # Baukonstruktion
    'BBL_WAND_TRAGEND': {'color': 1, 'description': 'Tragende Wände'},
    'BBL_WAND_NICHTTRAGEND': {'color': 3, 'description': 'Nichttragende Wände'},
    'BBL_FASSADE': {'color': 2, 'description': 'Fassadenlinie'},
    # Öffnungen
    'BBL_TUER': {'color': 6, 'description': 'Türen'},
    'BBL_FENSTER': {'color': 5, 'description': 'Fenster'},
    # Raumpolygone (Pflicht!)
    'BBL_RAUM_POLYGON': {'color': 30, 'description': 'Raumpolygone', 'required': True},
    'BBL_RAUM_NUMMER': {'color': 7, 'description': 'Raumnummern'},
}

BBL_OPTIONAL_LAYERS = {
    'BBL_WAND_GLAS': {'color': 4, 'description': 'Glaswände'},
    'BBL_STUETZE': {'color': 1, 'description': 'Stützen'},
    'BBL_DECKE': {'color': 8, 'description': 'Deckenöffnungen'},
    'BBL_TOR': {'color': 6, 'description': 'Tore'},
    'BBL_RAUM_BEZEICHNUNG': {'color': 7, 'description': 'Raumbezeichnung'},
    'BBL_RAUM_FLAECHE': {'color': 7, 'description': 'Flächenangabe'},
    'BBL_SANITAER': {'color': 160, 'description': 'Sanitärobjekte'},
    'BBL_HEIZUNG': {'color': 10, 'description': 'Heizkörper'},
    'BBL_LUEFTUNG': {'color': 130, 'description': 'Lüftungsauslässe'},
    'BBL_ELEKTRO': {'color': 40, 'description': 'Elektroanschlüsse'},
    'BBL_MOEBEL_FEST': {'color': 8, 'description': 'Feste Möbel'},
    'BBL_MOEBEL_LOSE': {'color': 9, 'description': 'Lose Möbel'},
    'BBL_TEXT': {'color': 7, 'description': 'Beschriftung'},
    'BBL_MASSLINIE': {'color': 7, 'description': 'Masslinien'},
    'BBL_ACHSE': {'color': 1, 'description': 'Achsen'},
    'BBL_NORDPFEIL': {'color': 7, 'description': 'Nordpfeil'},
}


class CAFMBasisplanValidator:
    """
    Validates CAD files against BBL CAFM Basisplan requirements.
    """

    def __init__(self, oda_converter_path: Optional[str] = None):
        """
        Initialize validator.

        Args:
            oda_converter_path: Path to ODA File Converter executable (optional)
        """
        self.oda_converter_path = oda_converter_path

    def validate_file(self, file_path: str) -> CADValidationResult:
        """
        Validate a DWG or DXF file.

        Args:
            file_path: Path to the CAD file

        Returns:
            CADValidationResult with all findings
        """
        if not EZDXF_AVAILABLE:
            result = CADValidationResult(filename=os.path.basename(file_path))
            result.errors.append(CADValidationError(
                rule_id="SYS-001",
                rule_name="System",
                severity=Severity.ERROR,
                message="ezdxf library not installed. Run: pip install ezdxf",
            ))
            return result

        filename = os.path.basename(file_path)
        result = CADValidationResult(filename=filename)

        # Handle DWG files (need conversion)
        if file_path.lower().endswith('.dwg'):
            dxf_path = self._convert_dwg_to_dxf(file_path)
            if dxf_path is None:
                result.errors.append(CADValidationError(
                    rule_id="DWG-001",
                    rule_name="Dateiformat",
                    severity=Severity.ERROR,
                    message="DWG-Datei konnte nicht konvertiert werden. Bitte laden Sie eine DXF-Datei hoch oder installieren Sie ODA File Converter.",
                ))
                return result
            file_path = dxf_path

        try:
            doc = ezdxf.readfile(file_path)
        except Exception as e:
            result.errors.append(CADValidationError(
                rule_id="DWG-001",
                rule_name="Dateiformat",
                severity=Severity.ERROR,
                message=f"Datei konnte nicht gelesen werden: {str(e)}",
            ))
            return result

        # Run all validations
        self._validate_drawing_setup(doc, result)
        self._validate_layers(doc, result)
        self._validate_room_polygons(doc, result)
        self._validate_blocks(doc, result)
        self._validate_xrefs(doc, result)
        self._collect_statistics(doc, result)

        return result

    def validate_bytes(self, file_bytes: bytes, filename: str) -> CADValidationResult:
        """
        Validate CAD file from bytes.

        Args:
            file_bytes: File content as bytes
            filename: Original filename

        Returns:
            CADValidationResult
        """
        # Write to temp file
        suffix = '.dxf' if filename.lower().endswith('.dxf') else '.dwg'
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        try:
            return self.validate_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def _convert_dwg_to_dxf(self, dwg_path: str) -> Optional[str]:
        """
        Convert DWG to DXF using ODA File Converter.

        Returns path to DXF file or None if conversion failed.
        """
        if not self.oda_converter_path or not os.path.exists(self.oda_converter_path):
            return None

        # Create temp directory for output
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = os.path.dirname(dwg_path)
            input_file = os.path.basename(dwg_path)

            try:
                # ODA File Converter command line:
                # ODAFileConverter "Input Folder" "Output Folder" ACAD2018 DXF 0 1
                subprocess.run([
                    self.oda_converter_path,
                    input_dir,
                    tmp_dir,
                    "ACAD2018",
                    "DXF",
                    "0",  # Recurse: 0=No
                    "1",  # Audit: 1=Yes
                    input_file,
                ], check=True, capture_output=True, timeout=60)

                # Find output DXF
                dxf_file = os.path.splitext(input_file)[0] + '.dxf'
                dxf_path = os.path.join(tmp_dir, dxf_file)

                if os.path.exists(dxf_path):
                    # Copy to persistent temp file
                    with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as out:
                        with open(dxf_path, 'rb') as f:
                            out.write(f.read())
                        return out.name

            except Exception:
                pass

        return None

    def _validate_drawing_setup(self, doc, result: CADValidationResult):
        """Validate drawing units and setup."""
        # Check units
        units = doc.header.get('$INSUNITS', 0)
        if units != 6:  # 6 = Meters
            result.errors.append(CADValidationError(
                rule_id="DWG-004",
                rule_name="Einheiten",
                severity=Severity.WARNING,
                message=f"Zeichnungseinheiten sind nicht auf Meter gesetzt (INSUNITS={units})",
            ))

        # Check for layouts
        layouts = [l.name for l in doc.layouts if l.name != 'Model']
        if not layouts:
            result.errors.append(CADValidationError(
                rule_id="DWG-013",
                rule_name="Layout",
                severity=Severity.WARNING,
                message="Kein Layout-Tab vorhanden (nur Modellbereich)",
            ))

    def _validate_layers(self, doc, result: CADValidationResult):
        """Validate layer structure against BBL standards."""
        existing_layers = {layer.dxf.name.upper(): layer for layer in doc.layers}
        result.layers_found = list(existing_layers.keys())

        # Check required layers
        for layer_name, spec in BBL_REQUIRED_LAYERS.items():
            if layer_name.upper() not in existing_layers:
                severity = Severity.ERROR if spec.get('required') else Severity.WARNING
                result.errors.append(CADValidationError(
                    rule_id=f"LAY-{layer_name[-3:]}",
                    rule_name="Layer-Struktur",
                    severity=severity,
                    message=f"Pflichtlayer fehlt: {layer_name} ({spec['description']})",
                    layer=layer_name,
                ))
            else:
                # Check layer color
                layer = existing_layers[layer_name.upper()]
                if layer.color != spec['color']:
                    result.errors.append(CADValidationError(
                        rule_id=f"LAY-{layer_name[-3:]}",
                        rule_name="Layer-Farbe",
                        severity=Severity.WARNING,
                        message=f"Layer {layer_name} hat falsche Farbe: {layer.color} (erwartet: {spec['color']})",
                        layer=layer_name,
                    ))

        # Check for non-BBL layers (info only)
        non_bbl_layers = [l for l in existing_layers.keys()
                         if not l.startswith('BBL_') and l not in ('0', 'DEFPOINTS')]
        if non_bbl_layers:
            result.statistics['non_bbl_layers'] = non_bbl_layers[:10]  # First 10

    def _validate_room_polygons(self, doc, result: CADValidationResult):
        """Validate room polygons on BBL_RAUM_POLYGON layer."""
        msp = doc.modelspace()

        # Find room polygons
        room_layer = 'BBL_RAUM_POLYGON'
        room_polygons = [e for e in msp.query(f'LWPOLYLINE[layer=="{room_layer}"]')]

        if not room_polygons:
            # Also check uppercase
            room_polygons = [e for e in msp.query('LWPOLYLINE')
                           if e.dxf.layer.upper() == room_layer.upper()]

        if not room_polygons:
            result.errors.append(CADValidationError(
                rule_id="RPO-001",
                rule_name="Raumpolygone",
                severity=Severity.ERROR,
                message=f"Keine Raumpolygone auf Layer {room_layer} gefunden",
                layer=room_layer,
            ))
            return

        result.room_count = len(room_polygons)
        total_area = 0.0

        for poly in room_polygons:
            # Check if closed
            if not poly.closed:
                result.errors.append(CADValidationError(
                    rule_id="RPO-002",
                    rule_name="Raumpolygon geschlossen",
                    severity=Severity.ERROR,
                    message=f"Raumpolygon ist nicht geschlossen",
                    layer=room_layer,
                    entity_handle=poly.dxf.handle,
                    location=self._get_centroid(poly),
                ))

            # Calculate area
            try:
                area = abs(self._calculate_polygon_area(poly))
                total_area += area

                # Check minimum area
                if area < 1.0:
                    result.errors.append(CADValidationError(
                        rule_id="RPO-005",
                        rule_name="Raumpolygon Mindestfläche",
                        severity=Severity.WARNING,
                        message=f"Raumpolygon hat sehr kleine Fläche: {area:.2f} m²",
                        layer=room_layer,
                        entity_handle=poly.dxf.handle,
                        location=self._get_centroid(poly),
                    ))
            except Exception:
                pass

        result.total_area = total_area

        # Check for overlapping polygons (simplified check)
        # Full overlap detection would require computational geometry library
        if len(room_polygons) > 1:
            result.statistics['room_overlap_check'] = 'Vereinfachte Prüfung - manuelle Kontrolle empfohlen'

    def _validate_blocks(self, doc, result: CADValidationResult):
        """Validate required blocks."""
        block_names = [b.name.upper() for b in doc.blocks if not b.name.startswith('*')]

        # Check for Plankopf
        has_plankopf = any('PLANKOPF' in name or 'TITLEBLOCK' in name for name in block_names)
        if not has_plankopf:
            result.errors.append(CADValidationError(
                rule_id="BLK-004",
                rule_name="Plankopf",
                severity=Severity.WARNING,
                message="Kein Plankopf-Block gefunden (BBL_PLANKOPF)",
            ))

        # Check for Nordpfeil
        has_nordpfeil = any('NORD' in name or 'NORTH' in name for name in block_names)
        if not has_nordpfeil:
            result.errors.append(CADValidationError(
                rule_id="BLK-003",
                rule_name="Nordpfeil",
                severity=Severity.WARNING,
                message="Kein Nordpfeil-Block gefunden (BBL_NORDPFEIL)",
            ))

        result.statistics['block_count'] = len(block_names)
        result.statistics['blocks'] = block_names[:20]  # First 20

    def _validate_xrefs(self, doc, result: CADValidationResult):
        """Check for external references."""
        xrefs = [b.name for b in doc.blocks if b.is_xref]
        if xrefs:
            result.errors.append(CADValidationError(
                rule_id="DWG-010",
                rule_name="Externe Referenzen",
                severity=Severity.ERROR,
                message=f"Externe Referenzen gefunden: {', '.join(xrefs)}. XREFs müssen aufgelöst werden.",
            ))

    def _collect_statistics(self, doc, result: CADValidationResult):
        """Collect drawing statistics."""
        msp = doc.modelspace()

        # Count entities by type
        entity_counts = {}
        for entity in msp:
            etype = entity.dxftype()
            entity_counts[etype] = entity_counts.get(etype, 0) + 1

        result.statistics['entity_counts'] = entity_counts
        result.statistics['total_entities'] = sum(entity_counts.values())

        # Count entities per layer
        layer_counts = {}
        for entity in msp:
            layer = entity.dxf.layer
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        result.statistics['entities_per_layer'] = dict(sorted(
            layer_counts.items(), key=lambda x: -x[1]
        )[:15])  # Top 15 layers

    def _calculate_polygon_area(self, polyline) -> float:
        """Calculate area of a polyline using shoelace formula."""
        points = list(polyline.get_points())
        if len(points) < 3:
            return 0.0

        n = len(points)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2.0

    def _get_centroid(self, polyline) -> Optional[Tuple[float, float]]:
        """Get approximate centroid of a polyline."""
        try:
            points = list(polyline.get_points())
            if not points:
                return None
            x = sum(p[0] for p in points) / len(points)
            y = sum(p[1] for p in points) / len(points)
            return (round(x, 2), round(y, 2))
        except Exception:
            return None


def get_bbl_layer_requirements() -> Dict[str, Any]:
    """Get BBL layer requirements for documentation."""
    return {
        'required': {k: v for k, v in BBL_REQUIRED_LAYERS.items()},
        'optional': {k: v for k, v in BBL_OPTIONAL_LAYERS.items()},
    }
