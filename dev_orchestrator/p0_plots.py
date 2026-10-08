"""Gráficos diagnósticos estáticos mediante Qt Charts ya disponible en el proyecto."""
def render(rows,path):
    import os
    os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
    from PySide6.QtWidgets import QApplication,QWidget,QGridLayout,QLabel
    from PySide6.QtCharts import QChart,QChartView,QLineSeries
    from pathlib import Path
    from PySide6.QtGui import QPainter,QFont,QFontDatabase
    app=QApplication.instance() or QApplication([])
    # El plugin offscreen Windows puede carecer de fuentes de sistema registradas.
    font_path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/segoeui.ttf'
    if font_path.is_file():
        identifier=QFontDatabase.addApplicationFont(str(font_path))
        families=QFontDatabase.applicationFontFamilies(identifier)
        if families: app.setFont(QFont(families[0],10))
    widget=QWidget(); layout=QGridLayout(widget)
    layout.addWidget(QLabel('Modelo 0D sintético — sin ondas ni escape sintonizado predictivo — sin validación experimental'),0,0,1,2)
    fields=(('W_C_J_per_cycle','Trabajo indicado [J/ciclo]'),('indicated_power_W','Potencia indicada [W]'),
        ('indicated_torque_Nm','Par indicado equivalente [N·m]'),('pmax_Pa','Presión máxima [Pa]'),
        ('completed_cycles','Ciclos completos'),('integration_seconds','Integración [s]'),
        ('minimum_step_deg','Mínimo medio paso [°]'),('rejected_steps','Rechazos'))
    for i,(key,title) in enumerate(fields):
        chart=QChart();series=QLineSeries()
        for row in rows: series.append(row['rpm'],row[key])
        chart.addSeries(series);chart.createDefaultAxes();chart.setTitle(title);chart.legend().hide()
        chart.axes()[0].setTitleText('RPM'); chart.axes()[0].setLabelFormat('%.0f')
        view=QChartView(chart);view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(view,1+i//2,i%2)
    widget.resize(1600,1600);widget.show();app.processEvents()
    if not widget.grab().save(str(path)): raise OSError('No se pudo guardar gráfico diagnóstico')
    widget.close()
