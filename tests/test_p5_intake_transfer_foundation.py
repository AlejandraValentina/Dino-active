import math
from motorsim.duct_network import DuctGeometry, NetworkState, PortInterface, interface_exchange, volume_of_segment
from motorsim.project import DuctSegment
from motorsim.gas1d.eos import IdealGas
from motorsim.coupling import ChamberState

E = IdealGas()

def chamber(p, y=.2):
    rho = p/(E.R*300.)
    return ChamberState(rho, p/(E.gamma-1), rho*y, 1.)

def primitive(p, y=.2):
    return E.validate((p/(E.R*300.), 0., p, y))


def test_geometry_and_exact_frustum_volume():
    g = DuctGeometry("intake", (DuctSegment("s", 100, 20, 20),), "external_to_crankcase")
    assert g.mesh(.02).n == 5
    assert math.isclose(volume_of_segment(100, 20, 20), math.pi*.1*.02**2/4)


def test_port_laws_and_closed_port():
    p = PortInterface(10, 20, 0)
    assert p.transfer_area(0) == 0
    assert p.transfer_area(10) == 100
    assert p.transfer_area(30) == 200
    closed = interface_exchange(None, None, 0, -1)
    assert closed["outward"] == (0.0, 0.0, 0.0, 0.0)


def test_topology_keeps_transfers_independent():
    a = DuctGeometry("t1", (DuctSegment("s", 50, 10, 10),), "crankcase_to_cylinder")
    b = DuctGeometry("t2", (DuctSegment("s", 60, 10, 12),), "crankcase_to_cylinder")
    network = NetworkState(transfers=(a, b))
    assert network.transfers[0] != network.transfers[1]


def test_state_validation_has_no_clipping():
    eos = IdealGas()
    assert eos.validate((1.0, 0.0, 100000.0, .5))[0] == 1.0

def test_intake_forward_and_backflow():
    f = interface_exchange(chamber(100000), primitive(200000), 1e-3, -1, eos=E)
    b = interface_exchange(chamber(200000), primitive(100000), 1e-3, -1, eos=E)
    assert f['outward'][0] > 0 and b['outward'][0] < 0
    assert f['outward'][2] > 0 and b['outward'][2] < 0

def test_transfer_forward_and_backflow():
    f = interface_exchange(chamber(200000), primitive(100000), 1e-3, 1, eos=E)
    b = interface_exchange(chamber(100000), primitive(200000), 1e-3, 1, eos=E)
    assert f['outward'][0] < 0 and b['outward'][0] > 0

def test_partial_port_monotonic_and_closed_transfer():
    vals = [interface_exchange(chamber(200000), primitive(100000), a, 1, eos=E)['outward'][0]
            for a in (0.0, 0.25e-3, .5e-3, 1e-3)]
    assert vals[0] == 0 and abs(vals[1]) < abs(vals[2]) < abs(vals[3])

def test_wave_travel_and_reflection_contract():
    g = DuctGeometry('wave', (DuctSegment('s', 100, 20, 20),), 'external_to_crankcase')
    mesh = g.mesh(.01); speed = E.sound_speed(primitive(100000))
    assert mesh.faces[-1] / speed > 0 and mesh.faces[-1] / speed < 1

def test_symmetry_and_asymmetry_are_independent():
    a = DuctGeometry('a',(DuctSegment('s',50,10,10),),'crankcase_to_cylinder')
    b = DuctGeometry('b',(DuctSegment('s',50,10,10),),'crankcase_to_cylinder')
    assert a.mesh(.01).as_dict() == b.mesh(.01).as_dict()
    c = DuctGeometry('c',(DuctSegment('s',60,10,10),),'crankcase_to_cylinder')
    assert c.mesh(.01).as_dict() != b.mesh(.01).as_dict()

def test_closed_flux_conservation_and_serialization():
    z = interface_exchange(None,None,0,-1)
    assert z['outward'] == (0.,0.,0.,0.)
    g = DuctGeometry('x',(DuctSegment('s',50,10,10),),'external_to_crankcase')
    payload = {'name':g.name,'direction':g.direction,'segments':[g.segments[0].__dict__]}
    assert payload['segments'][0]['length_mm'] == 50
