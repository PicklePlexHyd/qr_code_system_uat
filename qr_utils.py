import qrcode

def generate_qr(data, filename):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Save the QR code image
    try:
        print(f"Saving QR code to: {filename}")
        img.save(filename)
    except Exception as e:
        print(f"Error saving QR code: {e}")
        raise
