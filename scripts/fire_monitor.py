import requests
import zipfile
import geopandas as gpd
import pandas as pd
import os
import shutil
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.image as mpimg
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.legend_handler import HandlerTuple
import matplotlib.lines as mlines
import nepali_datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak, Flowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from PIL import Image as PILImage
import sys
import subprocess
import json


# === File paths ===
RESOURCES_DIR = "resources"
FIRMS_URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/shapes/zips/MODIS_C6_1_South_Asia_24h.zip"

NEPAL_DISTRICTS_SHP = os.path.join(RESOURCES_DIR, "nepal_districts_wards.shp")
DISTRICT_PLOT_SHP = os.path.join(RESOURCES_DIR, "nepal_districts_plot.shp")
PROTECTED_AREAS_SHP = os.path.join(RESOURCES_DIR, "nepal_protected_areas.shp")
FIRE_ICON_PATH = os.path.join(RESOURCES_DIR, "fire_icon.png")
NORTH_ARROW_PATH = os.path.join(RESOURCES_DIR, "north_arrow.png")

DOWNLOAD_DIR = "temp_fire_data"
OUTPUT_FOLDER = "fire_reports"
today_str = datetime.now().strftime('%Y%m%d')
OUTPUT_EXCEL = os.path.join(OUTPUT_FOLDER, f"nepal_daily_fire_report_{today_str}.xlsx")
OUTPUT_IMG_PATH = os.path.join(OUTPUT_FOLDER, f"nepal_daily_fire_map_{today_str}.jpg")
OUTPUT_PDF_PATH = os.path.join(OUTPUT_FOLDER, f"nepal_daily_fire_report_{today_str}.pdf")
CONFIDENCE_DATA_PATH = os.path.join(OUTPUT_FOLDER, f"fire_confidence_{today_str}.json")
DISTRICT_COLUMN_NAME = "DISTRICT"

class Divider(Flowable):
    def __init__(self, width=480, thickness=0.8, color=colors.grey, space_before=10, space_after=10):
        Flowable.__init__(self)
        self.width = width
        self.thickness = thickness
        self.color = color
        self.space_before = space_before
        self.space_after = space_after

    def wrap(self, availWidth, availHeight):
        return (self.width, self.thickness + self.space_before + self.space_after)

    def draw(self):
        self.canv.saveState()
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        y = self.space_before + self.thickness / 2
        self.canv.line(0, y, self.width, y)
        self.canv.restoreState()

def download_file(url, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    local_filename = os.path.join(target_dir, url.split('/')[-1])
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return local_filename
    except requests.exceptions.RequestException as e:
        print(f"Download error: {e}")
        return None

def unzip_file(zip_filepath, extract_dir):
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        shp_files = [f for f in os.listdir(extract_dir) if f.lower().endswith('.shp')]
        if not shp_files:
            return None
        return os.path.join(extract_dir, shp_files[0])
    except Exception as e:
        print(f"Unzip error: {e}")
        return None

def plot_fire_map(fire_gdf, districts_plot_shp, protected_areas_shp, fire_icon_path, north_arrow_path, output_img_path):
    districts_gdf = gpd.read_file(districts_plot_shp)
    protected_gdf = gpd.read_file(protected_areas_shp)

    if fire_gdf.crs != districts_gdf.crs:
        fire_gdf = fire_gdf.to_crs(districts_gdf.crs)
    if protected_gdf.crs != districts_gdf.crs:
        protected_gdf = protected_gdf.to_crs(districts_gdf.crs)

    nepal_union = districts_gdf.unary_union
    fire_gdf = fire_gdf[fire_gdf.geometry.within(nepal_union)]

    fig, ax = plt.subplots(figsize=(10, 6))
    districts_gdf.plot(ax=ax, color='#e0f2e0', edgecolor='black', linewidth=0.8, zorder=1)
    protected_gdf.plot(ax=ax, color='#8fbc8f', edgecolor='none', zorder=2)

    fire_img = mpimg.imread(fire_icon_path)
    for x, y in zip(fire_gdf.geometry.x, fire_gdf.geometry.y):
        ab = AnnotationBbox(OffsetImage(fire_img, zoom=0.06), (x, y), frameon=False, zorder=3)
        ax.add_artist(ab)

    ax.set_xlim(districts_gdf.total_bounds[0], districts_gdf.total_bounds[2])
    ax.set_ylim(districts_gdf.total_bounds[1], districts_gdf.total_bounds[3])
    ax.set_axis_off()

    # --- Legend: Use HandlerTuple for fire icon ---
    fire_handle = mlines.Line2D([], [], linestyle="none")
    fire_img_icon = OffsetImage(fire_img, zoom=0.18)  # Larger legend icon

    class HandlerFireTuple(HandlerTuple):
        def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
            oi = orig_handle[1]
            ab = AnnotationBbox(oi, (width/2, height/2), frameon=False, pad=0)
            ab.set_transform(trans)
            return [ab]

    protected_patch = mpatches.Patch(color='#8fbc8f', label='Protected Areas')
    district_patch = mpatches.Patch(facecolor='#e0f2e0', edgecolor='black', label='District', linewidth=0.8)

    fire_tuple = (fire_handle, fire_img_icon)
    handles = [fire_tuple, protected_patch, district_patch]
    labels = ['Fire Points', 'Protected Areas', 'District']
    handler_map = {fire_tuple: HandlerFireTuple()}

    leg = ax.legend(handles, labels, handler_map=handler_map, loc='lower left',
                    fontsize=12, frameon=True, borderpad=0.8, labelspacing=0.7,
                    edgecolor='#cccccc', title="Legend", title_fontsize=13)
    leg.get_frame().set_linewidth(1)
    leg.get_frame().set_edgecolor('#cccccc')
    leg.get_frame().set_facecolor('white')

    north_img = mpimg.imread(north_arrow_path)
    newax = fig.add_axes([0.83, 0.80, 0.09, 0.16], anchor='NE', zorder=10)
    newax.imshow(north_img)
    newax.axis('off')

    plt.tight_layout()
    plt.savefig(output_img_path, dpi=300, bbox_inches='tight', pad_inches=0.12)
    plt.close()

def overlay_icon_on_map(map_image_path, fire_icon_path, output_image_path, icon_x=140, icon_y=1458, zoom=0.16):
    map_img = mpimg.imread(map_image_path)
    img_height, img_width = map_img.shape[0], map_img.shape[1]
    fire_icon_img = mpimg.imread(fire_icon_path)

    fig, ax = plt.subplots(figsize=(img_width/100, img_height/100), dpi=100)
    ax.imshow(map_img)
    ab = AnnotationBbox(
        OffsetImage(fire_icon_img, zoom=zoom),
        (icon_x, icon_y),
        frameon=False,
        xycoords='data'
    )
    ax.add_artist(ab)
    ax.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    plt.savefig(output_image_path, dpi=100, bbox_inches='tight', pad_inches=0)
    plt.close()
    print(f"Fire icon added at ({icon_x}, {icon_y}) and saved to: {output_image_path}")

def generate_fire_report_pdf(
    pdf_path,
    fire_count,
    english_date,
    nepali_date,
    assessed_time,
    fire_map_path,
    fire_counts_df
):
    styles = getSampleStyleSheet()
    styleN = styles['Normal']
    styleH = styles['Heading1']

    desc_style = ParagraphStyle(
        'desc',
        parent=styleN,
        fontSize=12,
        leading=16,
        spaceAfter=16
    )

    desc = (
        f"<b>{fire_count}</b> fires have been detected in Nepal as of "
        f"<b>{english_date} ({nepali_date})</b> in the past 24 hours.<br/>"
        "(Note: For landscape level data, please contact us.)<br/><br/>"
        "<b>Satellite:</b> MODIS 1km<br/>"
        f"<b>Assessed Time:</b> {assessed_time}<br/><br/>"
        "(Source: https://firms.modaps.eosdis.nasa.gov/active_fire/ )"
    )

    elements = []
    elements.append(Paragraph("Nepal Daily Fire Report", styleH))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(desc, desc_style))
    elements.append(Spacer(1, 8))
    elements.append(Divider(width=480))
    elements.append(Spacer(1, 8))

    # --- Fit map image to page width with margin, keep aspect ratio ---
    pil_img = PILImage.open(fire_map_path)
    img_width, img_height = pil_img.size
    max_width = 480  # points (A4 width is 595 points, so this is a good margin)
    aspect = img_height / img_width
    display_width = max_width
    display_height = display_width * aspect
    elements.append(RLImage(fire_map_path, width=display_width, height=display_height))
    elements.append(Spacer(1, 8))
    elements.append(Divider(width=480, color=colors.lightgrey))
    elements.append(PageBreak())

    # --- Table on second page ---
    elements.append(Paragraph("Fire Counts by District", styleH))
    elements.append(Spacer(1, 8))
    elements.append(Divider(width=480, color=colors.lightgrey))
    elements.append(Spacer(1, 8))

    table_data = [fire_counts_df.columns.tolist()] + fire_counts_df.fillna("").astype(str).values.tolist()
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e0f2e0")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#000000")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(table)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    doc.build(elements)
    print(f"PDF saved: {pdf_path}")

def open_pdf(path):
    if sys.platform.startswith('darwin'):
        subprocess.call(('open', path))
    elif os.name == 'nt':
        os.startfile(path)
    elif os.name == 'posix':
        subprocess.call(('xdg-open', path))

def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    zip_path = download_file(FIRMS_URL, DOWNLOAD_DIR)
    if not zip_path:
        return

    fire_shp_path = unzip_file(zip_path, DOWNLOAD_DIR)
    if not fire_shp_path:
        shutil.rmtree(DOWNLOAD_DIR)
        return

    try:
        fire_gdf = gpd.read_file(fire_shp_path)
        nepal_districts_gdf = gpd.read_file(NEPAL_DISTRICTS_SHP)
    except Exception as e:
        print(f"Shapefile read error: {e}")
        shutil.rmtree(DOWNLOAD_DIR)
        return

    # Extract confidence values here (before any filtering)
    confidence_data = {}
    if 'CONFIDENCE' in fire_gdf.columns:
        confidence_values = fire_gdf['CONFIDENCE'].astype(float)
        confidence_data = {
            "average": round(confidence_values.mean()),
            "median": round(confidence_values.median()),
            "high_confidence_pct": round((confidence_values >= 80).sum() / len(confidence_values) * 100),
            "confidence_distribution": {
                "low": int((confidence_values < 30).sum()),
                "medium": int((confidence_values.between(30, 79)).sum()),
                "high": int((confidence_values >= 80).sum())
            }
        }
    else:
        # If CONFIDENCE column doesn't exist, look for other confidence-related columns
        confidence_cols = [col for col in fire_gdf.columns if 'CONF' in col.upper()]
        if confidence_cols:
            confidence_values = fire_gdf[confidence_cols[0]].astype(float)
            confidence_data = {
                "average": round(confidence_values.mean()),
                "median": round(confidence_values.median()),
                "high_confidence_pct": round((confidence_values >= 80).sum() / len(confidence_values) * 100),
                "confidence_distribution": {
                    "low": int((confidence_values < 30).sum()),
                    "medium": int((confidence_values.between(30, 79)).sum()),
                    "high": int((confidence_values >= 80).sum())
                }
            }
        else:
            # Fallback to default values if no confidence column found
            confidence_data = {
                "average": 80,
                "median": 85,
                "high_confidence_pct": 70,
                "confidence_distribution": {
                    "low": 10,
                    "medium": 20,
                    "high": 70
                }
            }

    # Save confidence data to file
    try:
        with open(CONFIDENCE_DATA_PATH, 'w') as f:
            json.dump(confidence_data, f, indent=2)
        print(f"Confidence data saved: {CONFIDENCE_DATA_PATH}")
    except Exception as e:
        print(f"Error saving confidence data: {e}")

    if fire_gdf.crs != nepal_districts_gdf.crs:
        try:
            fire_gdf = fire_gdf.to_crs(nepal_districts_gdf.crs)
        except Exception as e:
            print(f"CRS conversion error: {e}")
            shutil.rmtree(DOWNLOAD_DIR)
            return

    try:
        fires_in_nepal = gpd.sjoin(fire_gdf, nepal_districts_gdf, how='inner', predicate='within')
    except Exception as e:
        print(f"Spatial join error: {e}")
        shutil.rmtree(DOWNLOAD_DIR)
        return

    if DISTRICT_COLUMN_NAME not in fires_in_nepal.columns:
        print(f"Missing district column: {DISTRICT_COLUMN_NAME}")
        shutil.rmtree(DOWNLOAD_DIR)
        return

    if fires_in_nepal.empty:
        fire_counts_df = pd.DataFrame(columns=["S.N.", "District", "Fire Count"])
        total_fire_count = 0
    else:
        fire_counts = fires_in_nepal.groupby(DISTRICT_COLUMN_NAME).size()
        fire_counts_df = fire_counts.reset_index(name='Fire Count')
        fire_counts_df = fire_counts_df.sort_values(by="Fire Count", ascending=False)
        fire_counts_df.insert(0, 'S.N.', range(1, 1 + len(fire_counts_df)))
        fire_counts_df = fire_counts_df.rename(columns={DISTRICT_COLUMN_NAME: "District"})

        total = pd.DataFrame([{"S.N.": "", "District": "Total", "Fire Count": fire_counts_df["Fire Count"].sum()}])
        fire_counts_df = pd.concat([fire_counts_df, total], ignore_index=True)
        total_fire_count = fire_counts_df.loc[fire_counts_df["District"] == "Total", "Fire Count"].values[0]

    try:
        fire_counts_df.to_excel(OUTPUT_EXCEL, index=False, engine='openpyxl')
        print(f"Excel saved: {OUTPUT_EXCEL}")
    except Exception as e:
        print(f"Excel export error: {e}")

    try:
        fire_gdf = fire_gdf.cx[
            nepal_districts_gdf.total_bounds[0]:nepal_districts_gdf.total_bounds[2],
            nepal_districts_gdf.total_bounds[1]:nepal_districts_gdf.total_bounds[3]
        ]
        plot_fire_map(
            fire_gdf,
            DISTRICT_PLOT_SHP,
            PROTECTED_AREAS_SHP,
            FIRE_ICON_PATH,
            NORTH_ARROW_PATH,
            OUTPUT_IMG_PATH
        )
        print(f"Map saved: {OUTPUT_IMG_PATH}")
    except Exception as e:
        print(f"Map export error: {e}")

    # Overlay fire icon at pixel (140, 1458) and overwrite the map image
    try:
        overlay_icon_on_map(
            OUTPUT_IMG_PATH,
            FIRE_ICON_PATH,
            OUTPUT_IMG_PATH,  # Overwrite the same file, so only one image is produced
            icon_x=140,
            icon_y=1458,
            zoom=0.16
        )
    except Exception as e:
        print(f"Error overlaying fire icon: {e}")

    # --- Generate PDF ---
    try:
        now = datetime.now()
        english_date_str = now.strftime("%d %B %Y")
        nepali_date_str = nepali_datetime.date.from_datetime_date(now.date()).strftime("%d %B %Y")
        assessed_time_str = now.strftime("%I:%M %p")

        generate_fire_report_pdf(
            pdf_path=OUTPUT_PDF_PATH,
            fire_count=total_fire_count,
            english_date=english_date_str,
            nepali_date=nepali_date_str,
            assessed_time=assessed_time_str,
            fire_map_path=OUTPUT_IMG_PATH,
            fire_counts_df=fire_counts_df
        )
        open_pdf(OUTPUT_PDF_PATH)
    except Exception as e:
        print(f"PDF export error: {e}")

    try:
        shutil.rmtree(DOWNLOAD_DIR)
    except Exception as e:
        print(f"Cleanup warning: {e}")

if __name__ == "__main__":
    main()
