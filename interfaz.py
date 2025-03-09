from tkinter import *
from tkinter import messagebox, ttk
from logica import CuyesManagerLogic

class CuyesManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestión de Cuyes")
        self.root.geometry("1000x800")

        # Instancia de la lógica
        self.logica = CuyesManagerLogic()

        # Crear pestañas
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=BOTH, expand=True)

        # Pestañas
        self._crear_pestanas()

        # Cerrar conexión al salir
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _crear_pestanas(self):
        """Crea las pestañas de la interfaz."""
        self._crear_formulario_ingreso()
        self._crear_formulario_destete()
        self._crear_formulario_muertes_destetados()
        self._crear_formulario_ventas_destetados()
        self._crear_formulario_ventas_descarte()
        self._crear_formulario_gastos()
        self._crear_analisis_datos()
        self._crear_balance()

    def _crear_formulario_ingreso(self):
        """Crea el formulario de ingreso de datos."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Ingresar Datos")

        campos = [
            ("Número de galpón:", "galpon_entry"),
            ("Número de poza:", "poza_entry"),
            ("Número de cuyes reproductoras hembras:", "hembras_entry"),
            ("Número de cuyes reproductores machos:", "machos_entry"),
            ("Número de parto de la cuy reproductora:", "numero_parto_entry"),
            ("Número de cuyes nacidos en este parto:", "nacidos_entry"),
            ("Número de cuyes bebés muertos en este parto:", "muertos_bebes_entry"),
            ("Número de cuyes reproductores muertos:", "muertos_reproductores_entry"),
            ("Tiempo de cuyes reproductores (meses):", "tiempo_reproductores_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Guardar Datos", command=self.ingresar_datos).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def ingresar_datos(self):
        """Maneja el ingreso de datos."""
        try:
            galpon = self.galpon_entry.get()
            poza = self.poza_entry.get()
            hembras = int(self.hembras_entry.get())
            machos = int(self.machos_entry.get())
            numero_parto = int(self.numero_parto_entry.get())
            nacidos = int(self.nacidos_entry.get())
            muertos_bebes = int(self.muertos_bebes_entry.get())
            muertos_reproductores = int(self.muertos_reproductores_entry.get())
            tiempo_reproductores = int(self.tiempo_reproductores_entry.get())

            # Validar valores negativos
            if any(val < 0 for val in [hembras, machos, numero_parto, nacidos, muertos_bebes, muertos_reproductores, tiempo_reproductores]):
                raise ValueError("Los valores no pueden ser negativos.")

            resultado, mensaje = self.logica.ingresar_datos(galpon, poza, hembras, machos, numero_parto, nacidos, muertos_bebes, muertos_reproductores, tiempo_reproductores)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_formulario_destete(self):
        """Crea el formulario de registro de destete."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Registrar Destete")

        campos = [
            ("Número de galpón:", "destete_galpon_entry"),
            ("Número de poza:", "destete_poza_entry"),
            ("Número de cuyes destetados hembras:", "destete_hembras_entry"),
            ("Número de cuyes destetados machos:", "destete_machos_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Registrar Destete", command=self.registrar_destete).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def registrar_destete(self):
        """Maneja el registro de destete."""
        try:
            galpon = self.destete_galpon_entry.get()
            poza = self.destete_poza_entry.get()
            destetados_hembras = int(self.destete_hembras_entry.get())
            destetados_machos = int(self.destete_machos_entry.get())

            # Validar valores negativos
            if any(val < 0 for val in [destetados_hembras, destetados_machos]):
                raise ValueError("Los valores no pueden ser negativos.")

            resultado, mensaje = self.logica.registrar_destete(galpon, poza, destetados_hembras, destetados_machos)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_formulario_muertes_destetados(self):
        """Crea el formulario de registro de muertes de destetados."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Registrar Muertes de Destetados")

        campos = [
            ("Número de galpón:", "muertes_galpon_entry"),
            ("Número de poza:", "muertes_poza_entry"),
            ("Número de cuyes destetados hembras muertos:", "muertes_hembras_entry"),
            ("Número de cuyes destetados machos muertos:", "muertes_machos_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Registrar Muertes", command=self.registrar_muertes_destetados).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def registrar_muertes_destetados(self):
        """Maneja el registro de muertes de destetados."""
        try:
            galpon = self.muertes_galpon_entry.get()
            poza = self.muertes_poza_entry.get()
            muertos_hembras = int(self.muertes_hembras_entry.get())
            muertos_machos = int(self.muertes_machos_entry.get())

            # Validar valores negativos
            if any(val < 0 for val in [muertos_hembras, muertos_machos]):
                raise ValueError("Los valores no pueden ser negativos.")

            resultado, mensaje = self.logica.registrar_muertes_destetados(galpon, poza, muertos_hembras, muertos_machos)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_formulario_ventas_destetados(self):
        """Crea el formulario de registro de ventas de destetados."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Registrar Ventas de Destetados")

        campos = [
            ("Número de cuyes hembras vendidos:", "ventas_hembras_entry"),
            ("Número de cuyes machos vendidos:", "ventas_machos_entry"),
            ("Costo de venta:", "ventas_costo_entry"),
            ("Cuyes hembras dejados para futuros reproductores:", "ventas_futuros_hembras_entry"),
            ("Cuyes machos dejados para futuros reproductores:", "ventas_futuros_machos_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Registrar Venta", command=self.registrar_ventas_destetados).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def registrar_ventas_destetados(self):
        """Maneja el registro de ventas de destetados."""
        try:
            hembras_vendidas = int(self.ventas_hembras_entry.get())
            machos_vendidos = int(self.ventas_machos_entry.get())
            costo_venta = float(self.ventas_costo_entry.get())
            futuros_hembras = int(self.ventas_futuros_hembras_entry.get())
            futuros_machos = int(self.ventas_futuros_machos_entry.get())

            # Validar valores negativos
            if any(val < 0 for val in [hembras_vendidas, machos_vendidos, costo_venta, futuros_hembras, futuros_machos]):
                raise ValueError("Los valores no pueden ser negativos.")

            resultado, mensaje = self.logica.registrar_ventas_destetados(hembras_vendidas, machos_vendidos, costo_venta, futuros_hembras, futuros_machos)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_formulario_ventas_descarte(self):
        """Crea el formulario de registro de ventas de descarte."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Registrar Ventas de Descarte")

        campos = [
            ("Número de galpón:", "ventas_descarte_galpon_entry"),
            ("Número de poza:", "ventas_descarte_poza_entry"),
            ("Número de cuyes de descarte vendidos:", "ventas_descarte_cantidad_entry"),
            ("Costo de venta:", "ventas_descarte_costo_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Registrar Venta", command=self.registrar_ventas_descarte).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def registrar_ventas_descarte(self):
        """Maneja el registro de ventas de descarte."""
        try:
            galpon = self.ventas_descarte_galpon_entry.get()
            poza = self.ventas_descarte_poza_entry.get()
            cuyes_vendidos = int(self.ventas_descarte_cantidad_entry.get())
            costo_venta = float(self.ventas_descarte_costo_entry.get())

            # Validar valores negativos
            if any(val < 0 for val in [cuyes_vendidos, costo_venta]):
                raise ValueError("Los valores no pueden ser negativos.")

            resultado, mensaje = self.logica.registrar_ventas_descarte(galpon, poza, cuyes_vendidos, costo_venta)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_formulario_gastos(self):
        """Crea el formulario de registro de gastos."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Ingresar Gastos")

        campos = [
            ("Descripción del gasto:", "gastos_descripcion_entry"),
            ("Monto del gasto:", "gastos_monto_entry"),
            ("Tipo de gasto:", "gastos_tipo_entry")
        ]

        for i, (texto, nombre) in enumerate(campos):
            Label(frame, text=texto).grid(row=i, column=0, padx=10, pady=10)
            entry = Entry(frame)
            entry.grid(row=i, column=1, padx=10, pady=10)
            setattr(self, nombre, entry)

        Button(frame, text="Registrar Gasto", command=self.registrar_gastos).grid(row=len(campos), column=0, columnspan=2, pady=20)

    def registrar_gastos(self):
        """Maneja el registro de gastos."""
        try:
            descripcion = self.gastos_descripcion_entry.get()
            monto = float(self.gastos_monto_entry.get())
            tipo = self.gastos_tipo_entry.get()

            # Validar valores negativos
            if monto < 0:
                raise ValueError("El monto no puede ser negativo.")

            resultado, mensaje = self.logica.registrar_gastos(descripcion, monto, tipo)
            if resultado:
                messagebox.showinfo("Éxito", mensaje)
            else:
                messagebox.showerror("Error", mensaje)
        except ValueError as e:
            messagebox.showerror("Error", f"Valor inválido: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

    def _crear_analisis_datos(self):
        """Crea la pestaña de análisis de datos."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Análisis de Datos")

        self.tree = ttk.Treeview(frame, columns=("Galpón", "Poza", "Parto", "Hembras", "Machos", "Nacidos", "Muertos Bebés", "Muertos Reproductores", "Tiempo Reproductores", "Fecha Ingreso", "Fecha Descarte", "Fecha Nacimiento", "Destetados H", "Destetados M", "Muertos Destetados H", "Muertos Destetados M"), show="headings")
        self.tree.heading("Galpón", text="Galpón")
        self.tree.heading("Poza", text="Poza")
        self.tree.heading("Parto", text="Parto")
        self.tree.heading("Hembras", text="Hembras")
        self.tree.heading("Machos", text="Machos")
        self.tree.heading("Nacidos", text="Nacidos")
        self.tree.heading("Muertos Bebés", text="Muertos Bebés")
        self.tree.heading("Muertos Reproductores", text="Muertos Reproductores")
        self.tree.heading("Tiempo Reproductores", text="Tiempo Reproductores")
        self.tree.heading("Fecha Ingreso", text="Fecha Ingreso")
        self.tree.heading("Fecha Descarte", text="Fecha Descarte")
        self.tree.heading("Fecha Nacimiento", text="Fecha Nacimiento")
        self.tree.heading("Destetados H", text="Destetados H")
        self.tree.heading("Destetados M", text="Destetados M")
        self.tree.heading("Muertos Destetados H", text="Muertos Destetados H")
        self.tree.heading("Muertos Destetados M", text="Muertos Destetados M")
        self.tree.pack(fill=BOTH, expand=True)

        Button(frame, text="Actualizar Análisis", command=self.actualizar_analisis).pack(pady=10)

    def actualizar_analisis(self):
        """Actualiza el análisis de datos."""
        for row in self.tree.get_children():
            self.tree.delete(row)

        datos = self.logica.obtener_datos_analisis()
        for dato in datos:
            self.tree.insert("", END, values=(
                dato[0],  # Galpón
                dato[1],  # Poza
                dato[2],  # Número de parto
                dato[3],  # Hembras
                dato[4],  # Machos
                dato[5],  # Nacidos
                dato[6],  # Muertos bebés
                dato[7],  # Muertos reproductores
                dato[8],  # Tiempo reproductores
                dato[9],  # Fecha ingreso reproductores
                dato[10], # Fecha descarte
                dato[11], # Fecha nacimiento
                dato[12], # Destetados hembras
                dato[13], # Destetados machos
                dato[14], # Muertos destetados hembras
                dato[15]  # Muertos destetados machos
            ))

    def _crear_balance(self):
        """Crea la pestaña de balance."""
        frame = Frame(self.notebook)
        self.notebook.add(frame, text="Balance")

        Label(frame, text="Total ventas de destetados:").grid(row=0, column=0, padx=10, pady=10)
        self.total_ventas_destetados_label = Label(frame, text="0")
        self.total_ventas_destetados_label.grid(row=0, column=1, padx=10, pady=10)

        Label(frame, text="Total ventas de descarte:").grid(row=1, column=0, padx=10, pady=10)
        self.total_ventas_descarte_label = Label(frame, text="0")
        self.total_ventas_descarte_label.grid(row=1, column=1, padx=10, pady=10)

        Label(frame, text="Total gastos:").grid(row=2, column=0, padx=10, pady=10)
        self.total_gastos_label = Label(frame, text="0")
        self.total_gastos_label.grid(row=2, column=1, padx=10, pady=10)

        Label(frame, text="Balance final:").grid(row=3, column=0, padx=10, pady=10)
        self.balance_label = Label(frame, text="0")
        self.balance_label.grid(row=3, column=1, padx=10, pady=10)

        Button(frame, text="Actualizar Balance", command=self.actualizar_balance).grid(row=4, column=0, columnspan=2, pady=10)

    def actualizar_balance(self):
        """Actualiza el balance."""
        total_ventas_destetados, total_ventas_descarte, total_gastos, balance = self.logica.actualizar_balance()
        self.total_ventas_destetados_label.config(text=str(total_ventas_destetados))
        self.total_ventas_descarte_label.config(text=str(total_ventas_descarte))
        self.total_gastos_label.config(text=str(total_gastos))
        self.balance_label.config(text=str(balance))

    def on_closing(self):
        """Cierra la conexión a la base de datos antes de salir."""
        if hasattr(self.logica, 'cerrar_conexion'):
            self.logica.cerrar_conexion()  # Cierra la conexión a la base de datos
        else:
             print("Error: El método 'cerrar_conexion' no está disponible en la instancia de CuyesManagerLogic.")
        self.root.destroy()  # Cierra la ventana principal

if __name__ == "__main__":
    root = Tk()
    app = CuyesManagerGUI(root)
    root.mainloop()