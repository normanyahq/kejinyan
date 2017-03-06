run:
	python server.py

.PHONY: clean

clean:
	rm -rf file_storage *.db


tool.o: tool.cpp
	g++ tool.cpp -o s

tool: tool.o
