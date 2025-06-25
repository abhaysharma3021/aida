from app import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting ASID application on https://127.0.0.1:5000/")
    app.run(debug=True, ssl_context=('certs/cert.pem', 'certs/key.pem'))