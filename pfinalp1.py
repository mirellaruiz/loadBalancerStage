# Este script automatiza la creacion del escenario de pruebas de un balanceador de trafico, al que se conectan X servidores (entre 1 y 5) y 2 sistemas finales: c1 y un host.

#Se ejecutara pasandole un parametro obligatorio que definira la operacion a realizar:
# pfinalp1 <orden> <otros_parámetros>
# donde el parámetro <orden> puede tomar los valores siguientes:
# CREAR,
# ARRANCAR
# PARAR
# DESTRUIR


#!/usr/bin/python
import sys
import subprocess
import optparse
import time
from lxml import etree
import os.path

op = sys.argv[1]
serv = 2 

# Método de creación de los ficheros *.qcow2 de diferencias y los de especificación en XML de cada maquina virtual, así como los bridges virtuales que soportan las LAN del escenario.
def creacion(serv):
 	subprocess.call("pwd > fichero.txt", shell = True)
	rutaMal = ""	
	p1 = open("fichero.txt", "r")
	for line in p1:
		rutaMal = line
		break
	p1.close()
	ruta = rutaMal.replace("\n", "/")

    # Configuracion de los ficheros COW de LB y C1
	subprocess.call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 lb.qcow2", shell = True)
	subprocess.call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 c1.qcow2", shell = True)

	
    # Configuracion del fichero de especificacion de LB partiendo de la plantilla
    subprocess.call("cp plantilla-vm-p3.xml lb.xml", shell = True)
	tree = etree.parse("lb.xml")
	root = tree.getroot()
	name= root.find("name")
	name.text = "lb"
	print(name.text)
	source = root.find("./devices/disk/source")
	source.set("file", ""+ruta+"lb.qcow2")
	print(source.get("file"))
	    #Cambiar etiqueta interface
	bridge = root.find("./devices/interface/source")
	bridge.set("bridge","LAN2")
        #Meter interface nueva
	devices = root.find("devices")
	interface = etree.SubElement(devices, "interface")
	interface.set("type", "bridge")
	devices.append(interface)
        source = etree.SubElement(interface, "source")
	source.set("bridge", "LAN1")
	interface.append(source)
        model = etree.SubElement(devices, "model")
	model.set("type", "virtio")
	interface.append(model)
	tree.write("lb.xml")

    # Configuracion del fichero de especificacion de C1 partiendo de la plantilla
	subprocess.call("cp plantilla-vm-p3.xml c1.xml", shell = True)
	tree = etree.parse("c1.xml")
	root = tree.getroot()
	name= root.find("name")
	name.text = "c1"
	print(name.text)
	source = root.find("./devices/disk/source")
	source.set("file", ""+ruta+"c1.qcow2")
	print(source.get("file"))
        #Cambiar etiqueta interface
	bridge = root.find("./devices/interface/source")
	bridge.set("bridge","LAN1")
	tree.write("c1.xml")


    # Configuracion de los ficheros COW de los servidores
	for x in range(1,serv+1):
		subprocess.call("qemu-img create -f qcow2 -b cdps-vm-base-p3.qcow2 s"+str(x)+".qcow2", shell= True)
		subprocess.call("cp plantilla-vm-p3.xml s"+str(x)+".xml", shell = True)
		tree = etree.parse("s"+str(x)+".xml")
		#Configuracion del fichero de especificacion  de los servidores partiendo de la plantilla
		root = tree.getroot()
		name= root.find("name")
		name.text = "s"+str(x)+""
		source = root.find("./devices/disk/source")
		source.set("file", ruta+"s"+str(x)+".qcow2")
		bridge = root.find("./devices/interface/source")
		bridge.set("bridge","LAN2")
		tree.write("s"+str(x)+".xml")

    #  Creacion de los bridges correspondientes a las 2 redes virtuales
	subprocess.call("sudo brctl addbr LAN1", shell = True)
	subprocess.call("sudo ifconfig LAN1 up", shell = True)
	subprocess.call("sudo brctl addbr LAN2", shell = True)	
	subprocess.call("sudo ifconfig LAN2 up", shell = True)


# Metodo que se encarga de la configuracion y arranque de todas las maquinas virtuales
def configuracion(maquinas):	
	
	subprocess.call("mkdir -p mnt", shell = True)
	
    # Configuracion de red del host
	subprocess.call("sudo ifconfig LAN1 10.0.1.3/24", shell = True)
	subprocess.call("sudo ip route add 10.0.0.0/16 via 10.0.1.1", shell = True)		

    # Configuracion de red y arranque de C1
	subprocess.call("sudo vnx_mount_rootfs -s -r c1.qcow2 mnt", shell = True)
	time.sleep(0.1)
	subprocess.call("echo c1 > mnt/etc/hostname", shell = True)
	subprocess.call("sed -i 's/cdps cdps/c1/' mnt/etc/hosts ", shell = True)
	subprocess.call("cp mnt/etc/network/interfaces .", shell = True)	
	copia = open("interfaces", "r")
	interfaces = open("mnt/etc/network/interfaces", "w")
	for n in copia:
		if "iface lo inet loopback" in n:
			interfaces.write(n+ "\n" + "auto eth0" + "\n" + "iface eth0 inet static" + "\n" + "address 10.0.1.2" + "\n" + "netmask 255.255.255.0" + "\n" + "newtwork 10.0.1.0" + "\n" + "broadcast 10.0.1.255" + "\n" + "gateway 10.0.1.1")
		else:
			interfaces.write(n)
	interfaces.close()
	copia.close()	
	subprocess.call("cat mnt/etc/hostname", shell = True)
	subprocess.call("cat mnt/etc/hosts", shell = True)	
	subprocess.call("cat mnt/etc/network/interfaces", shell = True)
	subprocess.call("sudo vnx_mount_rootfs -u mnt", shell = True)
	subprocess.call("sudo virsh define c1.xml", shell = True)
	

    # Configuracion de red y arranque de LB
	subprocess.call("sudo vnx_mount_rootfs -s -r lb.qcow2 mnt", shell = True)
	time.sleep(0.1)
	subprocess.call("echo lb > mnt/etc/hostname", shell = True)
	subprocess.call("sed -i 's/cdps cdps/lb/' mnt/etc/hosts ", shell = True)
	subprocess.call("cp mnt/etc/network/interfaces .", shell = True)
	copia = open("interfaces", "r")
	interfaces = open("mnt/etc/network/interfaces", "w")
	for n in copia:
		if "iface lo inet loopback" in n:
			interfaces.write(n+ "\n" + "auto eth0" + "\n" + "iface eth0 inet static" + "\n" + "address 10.0.2.1" + "\n" + "netmask 255.255.255.0" + "\n" + "newtwork 10.0.2.0" + "\n" + "broadcast 10.0.2.255" + "\n" +  "auto eth1" + "\n" + "iface eth1 inet static" + "\n" + "address 10.0.1.1" + "\n" + "netmask 255.255.255.0" + "\n" + "newtwork 10.0.1.0" + "\n" + "broadcast 10.0.1.255" + "\n" )
		else:
			interfaces.write(n)
	interfaces.close()
	copia.close()
	subprocess.call("sed -i 's/#net.ipv4.ip_forward=1/net.ipv4.ip_forward=1/' mnt/etc/sysctl.conf", shell = True)	
	subprocess.call("cat mnt/etc/hostname", shell = True)
	subprocess.call("cat mnt/etc/hosts", shell = True)	
	subprocess.call("cat mnt/etc/network/interfaces", shell = True)

        # Configuración y arranque del balanceador de tráfico xr que hace disponible el servicio de balanceo de trafico entre servidores web
	backend = ""
	for x in range(1,maquinas+1):
		backend += "--backend 10.0.2."+str(x+10)+""
	balanceador = open("mnt/etc/rc.local", "w")
	balanceador.write("#!/bin/sh -e  \n  # rc.local \n service apache2 stop \n xr --verbose --server tcp:0:80 "+backend+ "--web-interface 0:8001 & \n exit 0 \n")

	balanceador.close()

	subprocess.call("sudo vnx_mount_rootfs -u mnt", shell = True)
	subprocess.call("sudo virsh define lb.xml", shell = True)
	

#   configuración y arranque de todos los servidores
	for x in range(1,maquinas+1):
		subprocess.call("sudo vnx_mount_rootfs -s -r s"+str(x)+".qcow2 mnt", shell = True)
		time.sleep(1)
		subprocess.call("echo s"+str(x)+" > mnt/etc/hostname", shell = True)
		subprocess.call("echo S"+str(x)+" > mnt/var/www/html/index.html", shell = True)
		subprocess.call("sed -i 's/cdps cdps/s"+str(x)+"/' mnt/etc/hosts ", shell = True)
		subprocess.call("cp mnt/etc/network/interfaces .", shell = True)
		copia = open("interfaces", "r")
		interfaces = open("mnt/etc/network/interfaces", "w")
		for n in copia:
			if "iface lo inet loopback" in n:
				interfaces.write(n+ "\n" + "auto eth0" + "\n" + "iface eth0 inet static" + "\n" + "address 10.0.2."+str(x+10)+"" + "\n" + "netmask 255.255.255.0" + "\n" + "newtwork 10.0.2.0" + "\n" + "broadcast 10.0.2.255" + "\n" + "gateway 10.0.2.1")
			else:
				interfaces.write(n)
		interfaces.close()
		copia.close()
		subprocess.call("cat mnt/etc/network/interfaces", shell = True)
		subprocess.call("cat mnt/etc/hostname", shell = True)
		subprocess.call("cat mnt/etc/hosts", shell = True)	
		subprocess.call("cat mnt/etc/network/interfaces", shell = True)
		subprocess.call("sudo vnx_mount_rootfs -u mnt", shell = True)
		subprocess.call("sudo virsh define s"+str(x)+".xml", shell = True)
		
		

#Metodo que arranca las maquinas virtuales y muestra su consola
def arrancar(maquinas):

	# Arrancar C1
	arrancarC1()

	# Arrancar LB
	arrancarLB()
	
	# Arrancar servidores
	for x in range(1,maquinas+1):
		arrancarServ(x)

# Los tres metodos siguientes arrancan cada maquina individualmente
def arrancarServ(arrancado):
		subprocess.call("sudo virsh start s"+str(arrancado)+"", shell = True)
		subprocess.call('xterm -e "sudo virsh console s'+str(arrancado)+'" &', shell = True)

def arrancarLB():
	subprocess.call("sudo virsh start lb", shell = True)
	subprocess.call('xterm -e "sudo virsh console lb" &', shell = True)

def arrancarC1():
	subprocess.call("sudo virsh start c1", shell = True)
	subprocess.call('xterm -e "sudo virsh console c1" &', shell = True)


#Metodo que se encarga de parar todas las maquinas virtuales
def parar(maquinas):

	# Parar C1
	pararC1()

	# Parar LB
	pararLB()
	
	# Parar servidores
	for x in range(1,maquinas+1):
		pararServ(x)

# Los tres metodos siguientes paran cada maquina individualmente
def pararServ(parado):
	subprocess.call("sudo virsh domstate s"+str(parado)+" > estadoS"+str(parado)+".txt", shell = True)
	estado = ""	
	p1 = open("estadoS"+str(parado)+".txt", "r")
	for line in p1:
		estado = line
		break
	p1.close()
	if estado.find("running") == -1:
		print("La maquina no esta arrancada")
	else:
		subprocess.call("sudo virsh shutdown s"+str(parado)+"", shell = True)

def pararLB():
	subprocess.call("sudo virsh domstate lb > estadoLB.txt", shell = True)
	estado = ""	
	p1 = open("estadoLB.txt", "r")
	for line in p1:
		estado = line
		break
	p1.close()
	if estado.find("running") == -1:
		print("La maquina no esta arrancada")
	else:
		subprocess.call("sudo virsh shutdown lb", shell = True)


def pararC1():
	subprocess.call("sudo virsh domstate c1 > estadoC1.txt", shell = True)
	estado = ""	
	p1 = open("estadoC1.txt", "r")
	for line in p1:
		estado = line
		break
	p1.close()
	if estado.find("running") == -1:
		print("La maquina no esta arrancada")
	else:
		subprocess.call("sudo virsh shutdown c1", shell = True)
			

#Metodo que se encarga de liberar el escenario, borrando todos los ficheros creados
def destruir(maquinas):

	# Destruir C1
	subprocess.call("sudo virsh destroy c1", shell = True)
	subprocess.call("sudo virsh undefine c1", shell = True)

	# Destruir LB
	subprocess.call("sudo virsh destroy lb", shell = True)
	subprocess.call("sudo virsh undefine lb", shell = True)
	
	# Destruir servidores
	for x in range(1,maquinas+1):
		subprocess.call("sudo virsh destroy s"+str(x)+"", shell = True)
		subprocess.call("sudo virsh undefine s"+str(x)+"", shell = True)
    
    # Destruir ficheros restantes: plantillas xml, ficheros .txt, etc.
	subprocess.call("rm -f s*", shell=True)
	subprocess.call("rm -f c1*", shell=True)
	subprocess.call("rm -f lb*", shell=True)
	subprocess.call("rm -f interfaces", shell=True)
	subprocess.call("rm -Rf mnt", shell=True)
	subprocess.call("rm -f maquinas.txt", shell=True)
	subprocess.call("rm -f fichero.txt", shell=True)
	subprocess.call("rm -f estado*", shell=True)
	subprocess.call("rm -f operacion.txt", shell=True)


#Metodo que se necarga de la monitorizacion del escenario que presenta el estado de todas las maquinas virtuales
def monitor():
	print("El estado de c1 es:")	
	subprocess.call("sudo virsh domstate c1", shell = True)	
	print("El estado de lb es:")
	subprocess.call("sudo virsh domstate lb", shell = True)	
	maq = open("maquinas.txt", "r")
	maquina = ""
	for n in maq:
		maquina = n
		break
	maq.close()
	for x in range(1,int(maquina)+1):
		print("El estado de s"+str(x)+"")
		subprocess.call("sudo virsh domstate s"+str(x)+"", shell = True)	


# pfinalp1 crear <otros_parámetros>
if op == "crear":

	if len(sys.argv) == 2 :
		subprocess.call("echo "+op+" > operacion.txt", shell=True)			
		subprocess.call("echo "+str(serv)+" > maquinas.txt", shell = True)
		serv = int(serv)
		creacion(serv)
		configuracion(serv)
	
	elif len(sys.argv) == 3:
		if sys.argv[2].isdigit() and int(sys.argv[2]) > 0 and int(sys.argv[2]) < 6:
			serv = sys.argv[2]
			subprocess.call("echo "+op+" > operacion.txt", shell=True)			
			subprocess.call("echo "+str(serv)+" > maquinas.txt", shell = True)
			serv = int(serv)
			creacion(serv)
			configuracion(serv)
		else:
			sys.stderr.write("Parametro invalido. Prueba: crear o crear 1, crear 2, crear 3, crear 4 o crear 5\n" )
		
	else:
			
     		sys.stderr.write("Parametro invalido. Prueba: crear o crear 1, crear 2, crear 3, crear 4 o crear 5\n" )

# pfinalp1 arrancar <otros_parámetros>
elif op == "arrancar":
	if len(sys.argv) == 2 or  len(sys.argv) == 3 :
		if os.path.isfile("operacion.txt"):
		
			maq = open("maquinas.txt", "r")
			maquina = ""
			for n in maq:
				maquina = n
				break
			maq.close()	
			if len(sys.argv) == 3 :
				if sys.argv[2] == "lb":
					arrancarLB()
				elif sys.argv[2] == "c1":
					arrancarC1()
				elif sys.argv[2].isdigit() and int(sys.argv[2]) > 0 and int(sys.argv[2]) < int(maquina)+1:
					arrancarServ(int(sys.argv[2]))
				else:
					sys.stderr.write("Parametro incorrecto: prueba: arrancar o arrancar + numero de servidor o lb o c1\n" )
			else:
				arrancar(int(maquina))
		else:
			sys.stderr.write("Crea las maquinas primero\n" )
	else:
		sys.stderr.write("Parametros incorrectos: prueba: arrancar o arrancar + numero de servidor o lb o c1\n" )	

# pfinalp1 parar <otros_parámetros>
elif op == "parar":
	if len(sys.argv) == 2 or  len(sys.argv) == 3 :
		if os.path.isfile("operacion.txt") :
			maq = open("maquinas.txt", "r")
			maquina = ""
			for n in maq:
				maquina = n
				break
			maq.close()
			if len(sys.argv) == 3:	
				if sys.argv[2] == "lb":
					pararLB()
				elif sys.argv[2] == "c1":
					pararC1()
				elif sys.argv[2].isdigit() and int(sys.argv[2]) > 0 and int(sys.argv[2]) < int(maquina)+1:
					pararServ(int(sys.argv[2]))
		
				else:
					sys.stderr.write("Parametro incorrecto: selecciona la maquina virtual a parar entre los que has arrancado o creado\n" )
			else:
				parar(int(maquina))
		else:
			sys.stderr.write("Crea las maquinas primero\n" )
	
	else:
		sys.stderr.write("Parametros incorrectos: prueba: parar o parar + numero de servidor o lb o c1\n" )

# pfinalp1 destruir
elif op == "destruir":
	if len(sys.argv) == 2:
	
		if os.path.isfile("operacion.txt") :
			maq = open("maquinas.txt", "r")
			maquina = ""
			for n in maq:
				maquina = n
				break
			maq.close()

			destruir(int(maquina))
		else:
			sys.stderr.write("Primero tendras que crear\n" )
	else:
		sys.stderr.write("Parametros incorrectos: prueba: destruir \n" )

# pfinalp1 monitor
elif op =="monitor":

	if len(sys.argv) == 2:
		if os.path.isfile("operacion.txt") :
			monitor()
		else:
			sys.stderr.write("No existen maquinas\n" )
	else:
		sys.stderr.write("Parametros incorrectos: prueba: monitor \n" )


else:
	sys.stderr.write("Parametro invalido. Prueba: crear, arrancar, parar, destruir, monitor \n" )

