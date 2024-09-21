import boto3
import flet as ft
from botocore.exceptions import ClientError
import requests

# AWS Keys
AWS_ACCESS_KEY_ID = "insert-access-key"
AWS_SECRET_ACCESS_KEY = "insert-secret-access-key"
AWS_REGION = "insert-aws-dynamodb-region" 

# DynamoDB Initialization
dynamodb = boto3.resource(
    'dynamodb',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY
)

gov_employees_table = dynamodb.Table('GovernmentEmployees')
drivers_table = dynamodb.Table('Drivers')

def get_employee_data(employee_id):
    try:
        response = gov_employees_table.get_item(Key={'ID': employee_id})
        return response.get('Item', None)
    except ClientError as e:
        print(f"Error fetching employee data: {e}")
        return None

def get_driver_data(driver_id):
    try:
        response = drivers_table.get_item(Key={'ID': driver_id})
        return response.get('Item', None)
    except ClientError as e:
        print(f"Error fetching driver data: {e}")
        return None

def update_driver_data(driver_id, update_expression, expression_values, expression_names=None):
    try:
        if all(len(val) > 0 for val in expression_values.values() if isinstance(val, set)):
            update_params = {
                'Key': {'ID': driver_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values
            }
            if expression_names:
                update_params['ExpressionAttributeNames'] = expression_names
            drivers_table.update_item(**update_params)
        else:
            print("Validation failed: One or more sets are empty.")
    except ClientError as e:
        print(f"Error updating driver data: {e}")

def update_employee_data(employee_id, update_expression, expression_values, expression_names=None):
    try:
        if all(len(val) > 0 for val in expression_values.values() if isinstance(val, set)):
            update_params = {
                'Key': {'ID': employee_id},
                'UpdateExpression': update_expression,
                'ExpressionAttributeValues': expression_values
            }
            if expression_names:
                update_params['ExpressionAttributeNames'] = expression_names
            gov_employees_table.update_item(**update_params)
        else:
            print("Validation failed: One or more sets are empty.")
    except ClientError as e:
        print(f"Error updating employee data: {e}")

def ensure_set_attribute_exists(table, item_id, attribute_name):
    """Ensures a set attribute exists for a given table, initializing it if necessary."""
    item = get_employee_data(item_id) if table == 'GovernmentEmployees' else get_driver_data(item_id)
    if attribute_name not in item:
        update_expression = f"SET {attribute_name} = :empty_set"
        update_data = {":empty_set": set()}
        if table == 'GovernmentEmployees':
            update_employee_data(item_id, update_expression, update_data)
        else:
            update_driver_data(item_id, update_expression, update_data)

def check_credentials(table, user_id, user_password):
    user_data = get_employee_data(user_id) if table == 'GovernmentEmployees' else get_driver_data(user_id)
    if user_data and user_data['Password'] == user_password:
        return user_data
    return None

def build_login_screen(title, id_text_field, password_text_field, switch_text, switch_callback, login_callback):
    return ft.Column(
        controls=[
            ft.Text(title, size=24, weight="bold"),
            id_text_field,
            password_text_field,
            ft.ElevatedButton("Entrar", on_click=login_callback),
            ft.TextButton(switch_text, on_click=switch_callback),
            ft.Text(value="", color="red", key="error_message")  
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20,
    )

def main(page: ft.Page):
    page.title = "Sistema de Transporte de Servidores (STS-PBH-SUFIS)"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = ft.padding.Padding(left=10, top=50, right=10, bottom=10)

    gov_employee_id = ft.TextField(label="ID", width=250)
    gov_employee_password = ft.TextField(label="Senha", password=True, width=250)

    driver_id = ft.TextField(label="ID", width=250)
    driver_password = ft.TextField(label="Senha", password=True, width=250)

    logout_button = ft.ElevatedButton("Sair", on_click=lambda e: show_employee_login(None))

    def login_employee(e):
        user_data = check_credentials('GovernmentEmployees', int(gov_employee_id.value), gov_employee_password.value)
        if user_data:
            show_drivers_list(user_data)
        else:
            page.controls[0].controls[4].value = "User not found. Try valid credentials."
            page.update()

    def login_driver(e):
        user_data = check_credentials('Drivers', int(driver_id.value), driver_password.value)
        if user_data:
            show_driver_dashboard(user_data)
        else:
            page.controls[0].controls[4].value = "User not found. Try valid credentials."
            page.update()

    def show_employee_login(e):
        page.controls.clear()
        page.vertical_alignment = "start"
        page.controls.append(
            build_login_screen(
                "Servidores", gov_employee_id, gov_employee_password, 
                "Mudar para o login de motoristas", show_driver_login, login_employee
            )
        )
        page.update()

    def show_driver_login(e):
        page.controls.clear()
        page.vertical_alignment = "start"
        page.controls.append(
            build_login_screen(
                "Motoristas", driver_id, driver_password, 
                "Mudar para o login de servidores", show_employee_login, login_driver
            )
        )
        page.update()

    def show_drivers_list(employee_data):
        page.controls.clear()
        page.scroll = "auto"
        page.vertical_alignment = "start"
        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: show_drivers_list(employee_data)), alignment=ft.alignment.top_left)],  
                alignment=ft.MainAxisAlignment.START
            )
        )
               
        driver_list_controls = [ft.Text("Lista de Motoristas", size=24, weight="bold")]

        try:
            response = drivers_table.scan()
            drivers = response['Items']
            for driver in drivers:
                if employee_data['Name'] in driver.get('RideRequests', []) or employee_data['Name'] in driver.get('Passengers', []):
                    continue  
                
                button = ft.TextButton(
                    f"{driver['Name']} - Status: {driver['Status']}",
                    on_click=lambda e, d_id=driver['ID']: show_driver_details(d_id, employee_data)
                )
                driver_list_controls.append(button)
        except ClientError as e:
            print(f"Error fetching drivers: {e}")

        show_cancel_button = any(employee_data['Name'] in driver.get('RideRequests', []) for driver in drivers)
        if show_cancel_button:
            driver_list_controls.append(
                ft.TextButton("Cancelar Solicitação de Motorista", on_click=lambda e: cancel_ride_request(employee_data))
            )

        share_location_button = ft.ElevatedButton(
            "Compartilhar",
            on_click=lambda e: share_location(employee_data, location_field.value)
        )
        location_field = ft.TextField(label="Inserir Link (Google Maps)", width=300)

        map_button = ft.ElevatedButton("Abrir Mapa", on_click=lambda e: show_map_employee(employee_data))

        geo = ft.Row(controls=[
            ft.Container(content=share_location_button),
            ft.Container(content=map_button)],
            alignment = ft.MainAxisAlignment.CENTER
        )

        driver_list_controls.append(location_field)
        driver_list_controls.append(geo)
        latest_location = ft.Text(f"Última localização: {employee_data['MapLocation']}")
        location_link = f"{employee_data['MapLocation']}"
        copy_location_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(location_link))
        driver_list_controls.append(latest_location)
        driver_list_controls.append(copy_location_button)

        driver_list = ft.Column(
            controls=driver_list_controls,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            scroll= "auto",
        )
        page.controls.append(driver_list)
        page.update()

    gps = ""

    def show_map_employee(employee_data):

        nonlocal gps

        page.controls.clear()
        page.scroll = "None"
        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Início", on_click=lambda e: show_drivers_list(employee_data)), alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: show_map_employee(employee_data)), alignment=ft.alignment.top_left)], 
                alignment=ft.MainAxisAlignment.START
            )
        )
        insert_location = ft.TextField(label="Inserir Link (Google Maps)", width=300)
        page.controls.append(insert_location)

        default_location = "https://www.google.com/maps"

        gps_coordinates = ft.Text(f"Coordenadas: {gps}")
        row = ft.Row(controls=[gps_coordinates])
        page.controls.append(row)
        generate_coordinates = ft.ElevatedButton("Gerar Coordenadas", on_click=lambda e: coordinates_generator(insert_location.value))
        copy_coordinates = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(gps))
        submit_button = ft.ElevatedButton("Submeter", on_click=lambda e: submit(insert_location.value))
        row2 = ft.Row(controls=[submit_button,generate_coordinates,copy_coordinates], scroll="auto")
        page.controls.append(row2)
        webview = ft.WebView(default_location, width=600, height=800)
        map = ft.Column(controls=[webview])
        page.controls.append(map)

        def coordinates_generator(insert_location):

            nonlocal gps
            nonlocal row
            nonlocal gps_coordinates
            
            if "search/" in insert_location:
                    coordinates_part = insert_location.split("search/")[1]
            else:
                return None
            
            if "," in coordinates_part:
                
                latitude = coordinates_part.split(",")[0]
                
                longitude = coordinates_part.split(",")[1]
                
                longitude = longitude.split("?")[0]

            if "-" in longitude:
                    longitude = longitude.split("+")[1]

            try:
                
                latitude = float(latitude)
                longitude = float(longitude)
                GPSLocation = f"{latitude}, {longitude}"
                gps = GPSLocation
                row.controls.remove(gps_coordinates)
                gps_coordinates = ft.Text(f"Coordenadas: {gps}")
                row.controls.append(gps_coordinates)
                page.update()
                return GPSLocation
                
            except ValueError:

                return None

        def submit(insert_location):
            
            nonlocal default_location
            nonlocal map
            nonlocal webview

            if insert_location:
                try:
                    response = requests.head(insert_location, allow_redirects=True)

                    full_url = response.url
        
                    if "maps" in full_url:
                        default_location = full_url
                        map.controls.remove(webview)  
                        webview = ft.WebView(default_location, width=600, height=800) 
                        map.controls.append(webview)
                        page.update() 
                        return default_location
                    else:
                        default_location = "https://www.google.com/maps"
                        return default_location
            
                except requests.RequestException as e:
                    print(f"Error expanding URL: {e}")
                    default_location = "https://www.google.com/maps"
                    return default_location
        
        page.update()   
        
    def show_driver_details(driver_id, employee_data):
        driver = get_driver_data(driver_id)
        page.controls.clear()
        page.scroll = "auto"

        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Início", on_click=lambda e: show_drivers_list(employee_data)), alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: show_driver_details(driver_id, employee_data)), alignment=ft.alignment.top_left)],  
                alignment=ft.MainAxisAlignment.START
            )
        )

        employee_name = employee_data['Name']
        send_request_text = "Enviar Solicitação de Motorista"
        send_request_enabled = True

        if employee_name in driver.get('Passengers', []):
            send_request_text = "Aceita"
            send_request_enabled = False
        elif employee_name in driver.get('RideRequests', []):
            send_request_text = "Enviada"
            send_request_enabled = False

        def send_ride_request(e):
            if employee_name not in driver.get("RideRequests", []) and employee_name not in driver.get("Passengers", []):
                update_driver_data(driver_id, "ADD RideRequests :r", {":r": {employee_name}})
                ensure_set_attribute_exists('Drivers', driver_id, "RideRequests")
                page.overlay.append(ft.SnackBar(ft.Text(f"Solicitação enviada para {driver['Name']}")))
                show_driver_details(driver_id, employee_data)

        location_link = driver.get("MapLocation", "https://www.google.com/maps")
        copy_location_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(location_link))
        contact = driver.get("Contact","Nenhuma informação")
        copy_contact_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(contact))


        webview = ft.WebView(location_link, width=600, height=400)

        details = ft.Column(
            controls=[
                ft.Text(f"Motorista:", size=20),
                ft.Text(f"Nome: {driver['Name']}"),
                ft.Text(f"Status: {driver['Status']}"),
                ft.Text(f"Contato: {driver['Contact']}"),
                copy_contact_button,
                ft.Text(f"Detalhamento: {driver['AdditionalDetails']}"),
                ft.Text(f"Passageiros: {', '.join(driver.get('Passengers', []))}"),
                ft.Text(f"Localização: {location_link}"),
                copy_location_button,
                ft.ElevatedButton(
                    send_request_text, 
                    on_click=send_ride_request,
                    disabled=not send_request_enabled
                ),webview
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        page.controls.append(details)
        page.update()

    def show_driver_dashboard(driver_data):
        page.controls.clear()
        page.scroll = "auto"
        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: refresh_driver_dashboard(driver_data)), alignment=ft.alignment.top_left)],  
                alignment=ft.MainAxisAlignment.START
            )
        )

        employee_list_button = ft.ElevatedButton(
            "Ver Servidores", 
            on_click=lambda e: show_employee_list(driver_data)
        )

        map_button = ft.ElevatedButton("Abrir Mapa", on_click=lambda e: show_map(driver_data))

        location_field = ft.TextField(label="Inserir Link (Google Maps)", width=300)

        share_location_button = ft.ElevatedButton(
            "Compartilhar",
            on_click=lambda e: share_driver_location(driver_data, location_field.value)
        )

        requests_controls = [ft.Text("Solicitações de Motorista:", size=20)]

        if "RideRequests" in driver_data and driver_data["RideRequests"]:
            for request in driver_data["RideRequests"]:
                accept_button = ft.ElevatedButton(
                    f"Aceitar solicitação de {request}",
                    on_click=lambda e, req=request: accept_ride_request(driver_data, req)
                )
                deny_button = ft.ElevatedButton(
                    f"Negar solicitação de {request}",
                    on_click=lambda e, req=request: deny_ride_request(driver_data, req)
                )
                requests_controls.extend([accept_button, deny_button])
        else:
            requests_controls.append(ft.Text("Nenhuma solicitação."))

        passenger_controls = [ft.Text("Gerenciar Passageiros:", size=20)]
        if "Passengers" in driver_data and driver_data["Passengers"]:
            for passenger in driver_data["Passengers"]:
                remove_button = ft.ElevatedButton(
                    f"Remover {passenger}",
                    on_click=lambda e, p=passenger: remove_passenger(driver_data, p)
                )
                passenger_controls.append(remove_button)

        status_buttons = ft.Row(
            controls=[
                ft.ElevatedButton("Mudar para Disponível", on_click=lambda e: update_driver_status(driver_data, "Disponível")),
                ft.ElevatedButton("Mudar para Dirigindo", on_click=lambda e: update_driver_status(driver_data, "Dirigindo")),
                ft.ElevatedButton("Mudar para Ausente", on_click=lambda e: update_driver_status(driver_data, "Ausente"))
            ],
            scroll="auto"
        )

        location_link = f"{driver_data['MapLocation']}"

        copy_location_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(location_link))

        dashboard = ft.Column(
            controls=[
                ft.Text(f"Bem-vindo, {driver_data['Name']}!", size=20),
                ft.Text(f"Status: {driver_data['Status']}", size=20),
                status_buttons,
                ft.Text(f"Última localização: {driver_data['MapLocation']}"),
                copy_location_button,
                location_field,
                ft.Row(controls=[
                share_location_button,
                map_button]),
                employee_list_button,
                ft.Column(controls=requests_controls, alignment=ft.MainAxisAlignment.CENTER, scroll = "auto"),
                ft.Text(f"Passageiros:", size=20),
                ft.Text(f"{', '.join(driver_data.get('Passengers', []))}"),
                ft.Column(controls=passenger_controls, alignment=ft.MainAxisAlignment.CENTER, scroll = "auto"),
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        page.controls.append(dashboard)
        page.update()

    gps2 = ""

    def show_map(driver_data):

        nonlocal gps2

        page.controls.clear()
        page.scroll = "None"
        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Início", on_click=lambda e: show_driver_dashboard(driver_data)), alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: show_map(driver_data)), alignment=ft.alignment.top_left)],  
                alignment=ft.MainAxisAlignment.START
            )
        )

        insert_location_2 = ft.TextField(label="Inserir Link (Google Maps)", width=300)
        page.controls.append(insert_location_2)
        
        default_location_2 = "https://www.google.com/maps"

        gps_coordinates = ft.Text(f"Coordenadas: {gps2}")
        row = ft.Row(controls=[gps_coordinates])
        page.controls.append(row)
        generate_coordinates = ft.ElevatedButton("Gerar Coordenadas", on_click=lambda e: coordinates_generator(insert_location_2.value))
        copy_coordinates = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(gps2))
        submit_button_2 = ft.ElevatedButton("Submeter", on_click=lambda e: submit_2(insert_location_2.value))
        row2 = ft.Row(controls=[submit_button_2,generate_coordinates,copy_coordinates],scroll="auto")
        page.controls.append(row2)
        webview_2 = ft.WebView(default_location_2, width=600, height=800)
        map_2 = ft.Column(controls=[webview_2])
        page.controls.append(map_2)

        def coordinates_generator(insert_location):

            nonlocal gps2
            nonlocal row
            nonlocal gps_coordinates
            
            if "search/" in insert_location:
                    coordinates_part = insert_location.split("search/")[1]
            else:
                return None
            
            if "," in coordinates_part:
                
                latitude = coordinates_part.split(",")[0]
                
                longitude = coordinates_part.split(",")[1]
                
                longitude = longitude.split("?")[0]

            if "-" in longitude:
                    longitude = longitude.split("+")[1]

            try:
                
                latitude = float(latitude)
                longitude = float(longitude)
                GPSLocation = f"{latitude}, {longitude}"
                gps2 = GPSLocation
                row.controls.remove(gps_coordinates)
                gps_coordinates = ft.Text(f"Coordenadas: {gps2}")
                row.controls.append(gps_coordinates)
                page.update()
                return GPSLocation
                
            except ValueError:

                return None

        def submit_2(insert_location_2):
            
            nonlocal default_location_2
            nonlocal map_2
            nonlocal webview_2

            if insert_location_2:
                try:
                    response = requests.head(insert_location_2, allow_redirects=True)

                    full_url = response.url
        
                    if "maps" in full_url:
                        default_location_2 = full_url
                        map_2.controls.remove(webview_2)  
                        webview_2 = ft.WebView(default_location_2, width=600, height=800) 
                        map_2.controls.append(webview_2)
                        page.update()
                        return default_location_2
                    else:
                        default_location_2 = "https://www.google.com/maps"
                        return default_location_2
            
                except requests.RequestException as e:
                    print(f"Error expanding URL: {e}")
                    default_location_2 = "https://www.google.com/maps"
                    return default_location_2
                
        page.update()
    
    def show_employee_list(driver_data):
        page.controls.clear()
        page.scroll = "auto"
        
        employee_list_controls = [
            ft.Row(
            controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                      ft.Container(content=ft.ElevatedButton("Início", on_click=lambda e: show_driver_dashboard(driver_data))),
                      ft.Container(content=ft.ElevatedButton("Atualizar"), on_click=lambda e: show_employee_list(driver_data))],
            alignment=ft.MainAxisAlignment.START),
            ft.Text("Servidores", size=24, weight="bold")
            ]

        try:
            response = gov_employees_table.scan()
            employees = response['Items']
            for employee in employees:
                button = ft.TextButton(
                    f"{employee['Name']}",
                    on_click=lambda e, emp_id=employee['ID']: show_employee_details(emp_id, driver_data)
                )
                employee_list_controls.append(button)
        except ClientError as e:
            print(f"Error fetching employees: {e}")

        employee_list = ft.Column(
            controls=employee_list_controls,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
        )
        page.controls.append(employee_list)
        page.update()

    def show_employee_details(employee_id, driver_data):
        employee = get_employee_data(employee_id)
        page.controls.clear()

        page.controls.append(
            ft.Row(
                controls=[ft.Container(content=logout_button, alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Servidores", on_click=lambda e: show_employee_list(driver_data)), alignment=ft.alignment.top_left),
                          ft.Container(content=ft.ElevatedButton("Atualizar", on_click=lambda e: show_employee_details(employee_id,driver_data)), alignment=ft.alignment.top_left)], 
                alignment=ft.MainAxisAlignment.START
            )
        )

        location_link = employee.get("MapLocation", "https://www.google.com/maps")
        copy_location_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(location_link))
        contact = employee.get("Contato","Nenhuma Informação")
        copy_contact_button = ft.ElevatedButton("Copiar", on_click=lambda e: page.set_clipboard(contact))

        webview = ft.WebView(location_link, width=600, height=500)

        details = ft.Column(
            controls=[
                ft.Text(f"Servidor:", size=20),
                ft.Text(f"Nome: {employee['Name']}"),
                ft.Text(f"Cargo: {employee['Role']}"),
                ft.Text(f"Contato: {employee['Contact']}"),
                copy_contact_button,
                ft.Text(f"Detalhamento: {employee['AdditionalDetails']}"),
                ft.Text(f"Localização: {location_link}"),
                copy_location_button,
                webview
            ],
            alignment=ft.MainAxisAlignment.CENTER
        )
        page.controls.append(details)
        page.update()

    def share_location(user_data, location_link):
        
        if location_link:
            try:
                response = requests.head(location_link, allow_redirects=True)

                full_url = response.url               
            
                if "Drivers" in user_data:
                    update_driver_data(user_data["ID"], "SET MapLocation = :loc", {":loc": full_url})
                    user_data["MapLocation"] = full_url
                else:
                    update_employee_data(user_data["ID"], "SET MapLocation = :loc", {":loc": full_url})
                    user_data["MapLocation"] = full_url

                page.overlay.append(ft.SnackBar(ft.Text("Location link shared successfully!")))
                if "Drivers" in user_data:
                    show_driver_dashboard(user_data)
                else:
                    show_drivers_list(user_data)

            except requests.RequestException as e:
                print(f"Error expanding URL: {e}")

        else:
            page.overlay.append(ft.SnackBar(ft.Text("Please enter a valid location link.")))

    def share_driver_location(user_data, location_link):
        
        if location_link:
            try:
                response = requests.head(location_link, allow_redirects=True)

                full_url = response.url               
            
                update_driver_data(user_data["ID"], "SET MapLocation = :loc", {":loc": full_url})
                
                user_data["MapLocation"] = full_url
                
                page.overlay.append(ft.SnackBar(ft.Text("Location link shared successfully!")))
                
                show_driver_dashboard(user_data)
          
            except requests.RequestException as e:
                print(f"Error expanding URL: {e}")


    def accept_ride_request(driver_data, employee_name):
        if employee_name in driver_data.get("RideRequests", []):
            update_driver_data(driver_data["ID"], "DELETE RideRequests :r ADD Passengers :p", {
                ":r": {employee_name}, 
                ":p": {employee_name}
            })
            ensure_set_attribute_exists('Drivers', driver_data["ID"], "Passengers")
            driver_data["RideRequests"].remove(employee_name)
            if "Passengers" not in driver_data:
                driver_data["Passengers"] = []
            driver_data["Passengers"].append(employee_name)
            page.overlay.append(ft.SnackBar(ft.Text(f"Ride request from {employee_name} accepted!")))
            show_driver_dashboard(driver_data)

    def deny_ride_request(driver_data, employee_name):
        if employee_name in driver_data.get("RideRequests", []):
            update_driver_data(driver_data["ID"], "DELETE RideRequests :r", {":r": {employee_name}})
            ensure_set_attribute_exists('Drivers', driver_data["ID"], "RideRequests")
            driver_data["RideRequests"].remove(employee_name)
            page.overlay.append(ft.SnackBar(ft.Text(f"Ride request from {employee_name} denied!")))
            show_driver_dashboard(driver_data)

    def refresh_driver_dashboard(driver_data):
        updated_data = get_driver_data(driver_data["ID"])
        if updated_data:
            show_driver_dashboard(updated_data)

    def update_driver_status(driver_data, new_status):
        update_expression = "SET #status = :s"
        expression_attribute_names = {"#status": "Status"}
        expression_attribute_values = {":s": new_status}

        try:
            drivers_table.update_item(
                Key={'ID': driver_data["ID"]},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values
            )
            driver_data["Status"] = new_status
            show_driver_dashboard(driver_data)
        except ClientError as e:
            print(f"Error updating driver status: {e}")

    def cancel_ride_request(employee_data):
        try:
            response = drivers_table.scan()
            drivers = response['Items']
            for driver in drivers:
                if employee_data['Name'] in driver.get('RideRequests', []):
                    update_driver_data(driver['ID'], "DELETE RideRequests :r", {":r": {employee_data['Name']}})
                    ensure_set_attribute_exists('Drivers', driver['ID'], 'RideRequests')
                    page.overlay.append(ft.SnackBar(ft.Text(f"Ride request canceled for driver {driver['Name']}")))
                    break
        except ClientError as e:
            print(f"Error fetching drivers for cancellation: {e}")
        show_drivers_list(employee_data)

    def remove_passenger(driver_data, passenger):
        update_driver_data(driver_data["ID"], "DELETE Passengers :p", {":p": {passenger}})
        ensure_set_attribute_exists('Drivers', driver_data["ID"], "Passengers")
        
        if passenger in driver_data["Passengers"]:
            driver_data["Passengers"].remove(passenger)
        
        page.overlay.append(ft.SnackBar(ft.Text(f"Passenger {passenger} removed.")))
        show_driver_dashboard(driver_data)

    show_employee_login(None)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
