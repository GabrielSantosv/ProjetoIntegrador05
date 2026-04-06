from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    try:
        from transformers import DonutProcessor, VisionEncoderDecoderModel
    except ImportError as exc:
        print("Instale transformers e torch para habilitar o script de IA.")
        print("pip install transformers torch pillow pdf2image")
        return 1

    try:
        from PIL import Image
        from pdf2image import convert_from_path
    except ImportError:
        print("Instale pillow e pdf2image para converter PDFs em imagens.")
        return 1

    model_name = "naver-clova-ix/donut-base-finetuned-docvqa"
    model_path = PROJECT_ROOT / "03_OUTPUT" / "ia_model"

    print("Carregando modelo Donut...")
    processor = DonutProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)

    sample_dir = PROJECT_ROOT / "01_DATA_INPUT"
    sample_files = sorted(sample_dir.rglob("*.pdf"))
    if not sample_files:
        print(f"Nenhum PDF encontrado em {sample_dir}.")
        return 1

    sample_pdf = sample_files[0]
    print(f"Usando arquivo de exemplo: {sample_pdf.name}")

    pages = convert_from_path(sample_pdf, dpi=300)
    image_path = PROJECT_ROOT / "03_OUTPUT" / "txt_extraidos" / f"{sample_pdf.stem}_page1.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(image_path, format="PNG")

    image = Image.open(image_path).convert("RGB")
    prompt = (
        "<s_docvqa><s_question>Qual é o nome completo do titular do documento?</s_question>"
        "<s_answer>"
    )
    decoder_input_ids = processor.tokenizer(
        prompt,
        add_special_tokens=False,
        return_tensors="pt",
    ).input_ids

    pixel_values = processor(image, return_tensors="pt").pixel_values
    outputs = model.generate(
        pixel_values,
        decoder_input_ids=decoder_input_ids,
        max_length=64,
        pad_token_id=processor.tokenizer.pad_token_id,
        eos_token_id=processor.tokenizer.eos_token_id,
        num_beams=1,
    )

    text = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
    print("Resposta do Donut:", text.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
