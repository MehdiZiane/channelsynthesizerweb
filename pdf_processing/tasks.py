# from celery import shared_task
# from .models import UploadedPDF
# from .processing import process_uploaded_pdf

# @shared_task
# def process_uploaded_pdf_task(uploaded_pdf_id):
#     uploaded_pdf = UploadedPDF.objects.get(id=uploaded_pdf_id)
#     process_uploaded_pdf(uploaded_pdf)
