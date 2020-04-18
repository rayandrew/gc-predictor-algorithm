# Java Benchmarks

Created by [Ray Andrew](mailto:raydreww@gmail.com)

## Benchmark Candidates

| Benchmark    | Year | Open Source | Free     |
|--------------|------|:-------------:|:----------:|
| [SPECjBB 2015](https://www.spec.org/jbb2015/) | 2015 | -           | -        |
| [SPECjvm2008](https://www.spec.org/jvm2008/)  | 2008 | -           | ✓      |
| [Java Grande](https://www.epcc.ed.ac.uk/research/computing/performance-characterisation-and-benchmarking/java-grande-benchmark-suite)  | 2000 | -           | Not sure |
| [Tuscany Bigbank Demo](https://svn.apache.org/repos/asf/tuscany/tags/java/sca-samples/1.0-incubator-M2/applications/bigbank/readme.html) | 2008 | ✓ | ✓ |
| [TPC-W](http://jmob.ow2.org/tpcw.html) | 2005 | ✓ | ✓ |
| [DayTrader](https://geronimo.apache.org/GMOxDOC20/daytrader.html) | 2005 | ✓ | ✓ |
| [ScalaBench](http://www.scalabench.org/) | 2011 | ✓ | ✓ |
| [Renaissance]([https://renaissance.dev/](https://renaissance.dev/)) | 2019 | ✓ | ✓ |
| [DaCapo](http://dacapobench.org/) | 2006 | ✓ | ✓ |

> Notes :
> In this document, only Renaissance, SPECjvm2008, and DaCapo will be explained

## Up and Running

### Download JARs

#### Dacapo

Go to this link https://sourceforge.net/projects/dacapobench/files/latest/download and copy the downloaded links

#### Renaissance

```bash
wget https://github.com/renaissance-benchmarks/renaissance/releases/download/v0.10.0/renaissance-gpl-0.10.0.jar
```

#### SPECjvm2008

```bash
wget ftp://ftp.spec.org/dist/osg/java/SPECjvm2008_1_01_setup.jar

# start installation in console mode, specify the installation dir
java -jar SPECjvm2008_1_01_setup.jar -i console

# from now on installation dir will be mentioned in SPECjvm2008_INSTALLATION_DIR
```

### Running

In this section, we can use either `nohup`, `screen`, or `tmux` for running the benchmarks in the background.

I personally prefer `nohup` because it is builtin in every `Linux` distro.

change every variables which denoted with `<>` bracket to suitable value.

#### Dacapo

```bash
nohup <JAVA_DIR>/java \
	-Xms<HEAP_SIZE> \
	-Xmx<HEAP_SIZE> \
	-Xloggc:<LOG_DIR>/gc.log \
	-Xlogucare:<LOG_DIR>/ucare.log \
	-XX:+PrintGCDetails \
	-XX:+PrintGCApplicationStoppedTime \
	-XX:+PrintGCApplicationConcurrentTime \
	-XX:+PrintGCDateStamps \
	-jar dacapo-9.12-MR1-bach.jar \
	--preserve \
	--debug \
	-n <NUM_ITERATIONS> \
	--ignore-validation \
	--validation-report /mnt/extra/benchmarks/logs/dacapo/report.log \
	--verbose \
	--no-pre-iteration-gc \
	--scratch-directory <LOG_DIR>/scratch/ \
	avrora eclipse fop h2 luindex lusearch lusearch-fix pmd sunflow xalan > <LOG_DIR>/nohup.log &
```

#### Renaissance

```bash
nohup <JAVA_DIR>/java \
	-Xms<HEAP_SIZE> \
	-Xmx<HEAP_SIZE> \
	-Xloggc:<LOG_DIR>/gc.log \
	-Xlogucare:<LOG_DIR>/ucare.log \
	-XX:+PrintGCDetails \
	-XX:+PrintGCApplicationStoppedTime \
	-XX:+PrintGCApplicationConcurrentTime \
	-XX:+PrintGCDateStamps \
	-jar renaissance-gpl-0.10.0.jar all \
	--csv <LOG_DIR>/result.csv > <LOG_DIR>/nohup.log &
```

#### SPECjvm2008

Create `specjvm.properties` file inside the `SPECjvm2008_INSTALLATION_DIR`

```properties
# specjvm.properties
# this configuration is compatible with OpenJDK8

specjvm.create.xml.report=true
specjvm.create.txt.report=true
specjvm.create.html.report=true
specjvm.benchmarks=startup.helloworld startup.compress startup.crypto.aes startup.crypto.rsa startup.crypto.signverify startup.mpegaudio startup.scimark.fft startup.scimark.lu startup.scimark.monte_carlo startup.scimark.sor startup.scimark.sparse startup.serial startup.sunflow startup.xml.transform startup.xml.validation compress crypto.aes crypto.rsa crypto.signverify derby mpegaudio scimark.fft.large scimark.lu.large scimark.sor.large scimark.sparse.large scimark.fft.small scimark.lu.small scimark.sor.small scimark.sparse.small scimark.monte_carlo serial sunflow xml.transform xml.validation
```

```bash
cd <SPECjvm2008_INSTALLATION_DIR> # must cd into this folder or you will get benchmarks are not defined

nohup <JAVA_DIR>/java \
	-Xms<HEAP_SIZE> \
	-Xmx<HEAP_SIZE> \
	-Xloggc:<LOG_DIR>/gc.log \
	-Xlogucare:<LOG_DIR>/ucare.log \
	-XX:+PrintGCDetails \
	-XX:+PrintGCApplicationStoppedTime \
	-XX:+PrintGCApplicationConcurrentTime \
	-XX:+PrintGCDateStamps \
	-jar ./SPECjvm2008.jar \
	-pf specjvm.properties -crf true -ctf true -chf true -v --ignoreCheckTest > <LOG_DIR>/nohup.log &
```
