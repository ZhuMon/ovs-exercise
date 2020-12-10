PCAP_DIR = pcaps
LOG_DIR = logs

TOPO = topology.json

all: mininet

mininet:
	sudo python3 run_mininet.py -t $(TOPO)

stop:
	sudo mn -c

clean: stop
	rm -f *.pyc
