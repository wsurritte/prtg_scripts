// Based on things I found online
// intended to be compiled

const { exec } = require('child_process');

function getAllHardDrives() {
  return new Promise((resolve, reject) => {
    exec('lsblk -d -n -o NAME,MODEL', (error, stdout, stderr) => {
      if (error) {
        reject(`Error executing lsblk: ${error}`);
        return;
      }

      if (stderr) {
        reject(`lsblk returned an error: ${stderr}`);
        return;
      }

 const driveList = stdout
        .split('\n')
        .filter(Boolean)
        .map(line => {
          const [name, ...modelArray] = line.split(/\s+/);
          const model = modelArray.join(' ').trim();
          return { name, model };
        });

     resolve(driveList);
    });
  });
}

function getHardDriveTemperatures(drive) {
  return new Promise((resolve, reject) => {
    exec(`smartctl -a /dev/${drive.name}`, (error, stdout, stderr) => {
      if (error) {
        if (error.code === 64) {
        } else {
          reject(`Error executing smartctl: ${error}`);
          return;
        }
      }

      if (stderr) {
        console.warn(`smartctl returned a non-fatal error: ${stderr}`);
      }

      const lines = stdout.split('\n');

      // Check if the drive is NVMe
      const isNVMe = lines.some(line => line.includes('NVMe'));

      // Use the appropriate keyword for temperature based on drive type
      const temperatureKeyword = isNVMe ? 'Temperature Sensor 1:' : 'Temperature_Celsius';

      const temperatureLine = lines.find(line => line.includes(temperatureKeyword));

      if (!temperatureLine) {
        console.warn(`Temperature information not found for ${drive.name}`);
        resolve({
          channel: `${drive.model} (${drive.name})`,
          value: null,
          unit: 'custom',
          customunit: '°F',
          float: true,
        });
        return;
      }

      let temperatureCelsius = null;

      // Extract the temperature value
      if (isNVMe) {
        const temperatureMatch = temperatureLine.match(/(\d+)\sCelsius/);

        if (!temperatureMatch) {
          console.warn(`Temperature value not found for ${drive.name}`);
          resolve({
            channel: `${drive.model} (${drive.name})`,
            value: null,
            unit: 'custom',
            customunit: '°F',
            float: true,
          });
          return;
        }

        temperatureCelsius = parseInt(temperatureMatch[1], 10);
      } else {
        temperatureCelsius = parseInt(temperatureLine.split(/\s+/)[9], 10);
      }

      const temperatureFahrenheit = (temperatureCelsius * 9/5) + 32;

      resolve({
        channel: `${drive.model} (${drive.name})`,
        value: temperatureFahrenheit,
        unit: 'custom',
        customunit: '°F',
        float: true,
      });
    });
  });
}

async function main() {
  try {
    const mode = process.argv[2];

    if (mode === 'list') {
      const drives = await getAllHardDrives();
      console.log('List of hard drives:', drives.map(drive => `${drive.name} (${drive.model})`).join(', '));
    } else if (mode === 'temperatures') {
      const drives = await getAllHardDrives();
      const temperaturePromises = drives.map(drive => getHardDriveTemperatures(drive));
      const temperatures = await Promise.all(temperaturePromises);

      // Format the temperatures in PRTG JSON format
      const prtgJson = {
        prtg: {
          result: temperatures.map(temp => ({
            channel: temp.channel,
            value: temp.value,
            unit: temp.unit,
            customunit: temp.customunit,
            float: temp.float,
          })),
        },
      };

      console.log(JSON.stringify(prtgJson, null, 2));
    } else {
      console.log('Invalid mode. Please use "list" or "temperatures".');
    }
  } catch (err) {
    console.error(err);
  }
}

main();
