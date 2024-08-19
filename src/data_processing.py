import subprocess
import os
import fitz  # PyMuPDF
import pikepdf  # for PDF optimization
import os
import aspose.words as aw
import pikepdf


def search_for_text(document, search_text, start_page=0):
    """
    PDF 문서 내에서 특정 텍스트를 검색하여 해당 페이지 번호를 반환합니다.

    Args:
        document: PDF 문서 객체.
        search_text (str): 검색할 텍스트.
        start_page (int): 검색을 시작할 페이지 번호 (0부터 시작).

    Returns:
        int: 검색된 텍스트가 있는 페이지 번호. 찾지 못한 경우 -1을 반환.
    """
    for page_num in range(start_page, document.page_count):
        page = document.load_page(page_num)
        text = page.get_text()
        if search_text in text:
            return page_num

    return -1


def compress_pdf(input_path, output_path, image_quality=10):
    """
    PDF 내 이미지의 품질을 낮춰 PDF 파일의 크기를 줄입니다.

    Args:
        input_path (str): 원본 PDF 파일 경로.
        output_path (str): 최종 저장할 PDF 파일 경로.
        image_quality (int): 이미지 품질 수준 (1-100).

    Note:
        이미지 품질을 낮추어 용량을 줄이지만, 본문 텍스트나 레이아웃에 영향을 미칠 수 있음.
    """
    with pikepdf.open(input_path) as pdf:
        for page in pdf.pages:
            for image in page.images:
                with pdf.open_image(image) as img:
                    img.compress(pikepdf.ImageFormat.JPEG, quality=image_quality)
        pdf.save(output_path)


def compress_pdf_with_ghostscript(input_path, output_path):
    """
    Ghostscript를 사용하여 PDF 파일의 크기를 최적화합니다.

    Args:
        input_path (str): 원본 PDF 파일 경로.
        output_path (str): 최종 저장할 PDF 파일 경로.
    """
    gs_command = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/screen",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path,
    ]
    subprocess.run(gs_command)


def extract_pages(pdf_path, output_path, start_tag, end_tag):
    """
    PDF에서 특정 페이지 범위를 추출하여 새 PDF로 저장하고, 용량을 최적화합니다.

    Args:
        pdf_path (str): 원본 PDF 파일 경로.
        output_path (str): 추출된 페이지를 저장할 PDF 파일 경로.
        start_tag (str): 시작 페이지를 찾기 위한 검색 텍스트.
        end_tag (str): 종료 페이지를 찾기 위한 검색 텍스트.

    Returns:
        int: 추출된 페이지 수. 해당 섹션을 찾지 못한 경우 -1을 반환.
    """
    document = fitz.open(pdf_path)
    new_document = fitz.open()

    start_page = search_for_text(document, start_tag, start_page=5)
    if start_page == -1:
        print(f"Start tag '{start_tag}' not found.")
        return

    end_page = search_for_text(document, end_tag, start_page=start_page + 1)
    if end_page == -1:
        print(f"End tag '{end_tag}' not found.")
        return

    for page_num in range(start_page, end_page + 1):
        new_document.insert_pdf(document, from_page=page_num, to_page=page_num)

    temp_output_path = output_path.replace(".pdf", "_temp.pdf")
    new_document.save(temp_output_path)
    print(f"Extracted pages {start_page} to {end_page}")

    # PDF 최적화 (용량 감소)
    compress_pdf_with_ghostscript(temp_output_path, output_path)

    os.remove(temp_output_path)
    print(f"Optimized PDF saved as {output_path}")

    if (end_page - start_page) < 1:
        os.remove(output_path)
        return -1
    else:
        return end_page - start_page


def get_tags_for_year(year):
    """
    특정 연도에 해당하는 섹션 시작 및 종료 태그를 반환합니다.
    연도에 따라 섹션의 명칭이 다르기 때문에, 오류가 있을 수 있습니다.

    Args:
        year (int): 연도.

    Returns:
        tuple: (start_tag, end_tag) 형태로 반환.

    Raises:
        ValueError: 지정된 연도가 범위를 벗어난 경우 발생.
    """
    if year == 2024:
        start_tag = "VI. 이사회 등 회사의 기관에 관한 사항"
        end_tag = "VII. 주주에 관한 사항"
    elif 2021 <= year <= 2023:
        start_tag = "VI. 이사회 등 회사의 기관에 관한 사항"
        end_tag = "VII. 주주에 관한 사항"
    elif 2014 <= year <= 2020:
        start_tag = ". 이사회 등 회사의 기관 및 계열회사에 관한 사항"
        end_tag = ". 주주에 관한 사항"
    elif 2009 <= year <= 2013:
        start_tag = ". 이사회 등 회사의 기관 및 계열회사에 관한 사항"
        end_tag = ". 주주에 관한 사항"
    elif 2007 <= year <= 2008:
        start_tag = "V. 이사회 등 회사의 기관 및 계열회사에 관한 사항"
        end_tag = "VI. 주주에 관한 사항"
    elif year == 2006:
        start_tag = ". 이사회 등 회사의 기관 및 계열회사에 관한 사항"
        end_tag = ". 주주에 관한 사항"
    elif 2000 <= year <= 2005:
        start_tag = ". 지배구조 및 관계회사등의 현황"
        end_tag = ". 주식에 관한 사항"
    else:
        raise ValueError(f"Year {year} is out of the predefined range")

    return start_tag, end_tag


# PDF를 이미지로 변환하여 새로운 PDF로 저장하는 함수
def resize_pdf(input_path, output_path, image_quality=80):
    renderer = aw.pdf2word.fixedformats.PdfFixedRenderer()
    pdf_read_options = aw.pdf2word.fixedformats.PdfFixedOptions()
    pdf_read_options.image_format = aw.pdf2word.fixedformats.FixedImageFormat.JPEG
    pdf_read_options.jpeg_quality = image_quality

    with open(input_path, "rb") as pdf_stream:
        pages_stream = renderer.save_pdf_as_images(pdf_stream, pdf_read_options)

    builder = aw.DocumentBuilder()
    for i in range(len(pages_stream)):
        max_page_dimension = 1584
        page_setup = builder.page_setup
        set_page_size(page_setup, max_page_dimension, max_page_dimension)

        page_image = builder.insert_image(pages_stream[i])

        set_page_size(page_setup, page_image.width, page_image.height)
        page_setup.top_margin = 0
        page_setup.left_margin = 0
        page_setup.bottom_margin = 0
        page_setup.right_margin = 0

        if i != len(pages_stream) - 1:
            builder.insert_break(aw.BreakType.SECTION_BREAK_NEW_PAGE)

    save_options = aw.saving.PdfSaveOptions()
    save_options.cache_background_graphics = True

    builder.document.save(output_path, save_options)


# PDF 페이지의 크기를 설정하는 함수
def set_page_size(page_setup, width, height):
    page_setup.page_width = width
    page_setup.page_height = height


# 디렉토리 내 모든 PDF 파일을 처리하는 함수
def process_directory(directory_path):
    for root, _, files in os.walk(directory_path):
        for file in files:
            if file.lower().endswith(".pdf"):
                input_path = os.path.join(root, file)
                output_path = os.path.join(root, f"resized/{file}")
                resize_pdf(input_path, output_path)
                print(f"Saved to {output_path}")


# PDF 파일의 이미지를 압축하여 파일 크기를 줄이는 함수
def compress_pdf(input_path, output_path, image_quality=10):
    with pikepdf.open(input_path) as pdf:
        for page in pdf.pages:
            page_obj = pikepdf.Page(page)
            for image_name, image_obj in page_obj.images.items():
                with pdf.open_image(image_obj) as img:
                    img.save(image_obj, format="JPEG", quality=image_quality)
        pdf.save(output_path)
