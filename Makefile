PCAP_DIR = pcaps
LOG_DIR = logs

TOPO = topology.json
CONTROLLER = simple_switch_13.py

all: mininet

mininet:
	sudo python3 run_mininet.py -t $(TOPO) -c $(CONTROLLER)

stop:
	sudo mn -c

clean: stop
	rm -f *.pyc
