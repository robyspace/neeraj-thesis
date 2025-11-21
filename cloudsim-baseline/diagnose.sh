#!/bin/bash

# CloudSim Plus Diagnostic Script
# Run this from your cloudsim-baseline directory

echo "======================================"
echo "  CloudSim Plus Diagnostics"
echo "======================================"
echo ""

# Check current directory
echo "Current directory: $(pwd)"
echo ""

# Check 1: Show dependencies section of pom.xml
echo "1. Your pom.xml dependencies:"
echo "-----------------------------------"
if [ -f "pom.xml" ]; then
    sed -n '/<dependencies>/,/<\/dependencies>/p' pom.xml
else
    echo "ERROR: pom.xml not found!"
    exit 1
fi

echo ""
echo "2. Checking Maven dependency tree..."
echo "-----------------------------------"
mvn dependency:tree | head -50

echo ""
echo "3. Checking local Maven repository..."
echo "-----------------------------------"
echo "Looking for CloudSim Plus in: ~/.m2/repository/org/cloudsimplus/"
ls -la ~/.m2/repository/org/cloudsimplus/ 2>/dev/null || echo "Directory does not exist - CloudSim Plus NOT downloaded!"

echo ""
echo "4. Checking if CloudSim Plus classes are in your JAR..."
echo "-----------------------------------"
if [ -f "target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar" ]; then
    echo "Searching for CloudSim Plus classes in JAR:"
    jar tf target/cloudsim-baseline-1.0-SNAPSHOT-jar-with-dependencies.jar | grep "org/cloudsimplus" | head -10
    
    if [ $? -ne 0 ]; then
        echo "✗ NO CloudSim Plus classes found in JAR!"
    fi
else
    echo "JAR file not found"
fi

echo ""
echo "5. Checking your SimpleTest.java imports..."
echo "-----------------------------------"
if [ -f "src/main/java/org/example/SimpleTest.java" ]; then
    echo "Import statements:"
    grep "^import" src/main/java/org/example/SimpleTest.java | head -10
else
    echo "SimpleTest.java not found"
fi

echo ""
echo "======================================"
echo "  Diagnosis Complete"
echo "======================================"